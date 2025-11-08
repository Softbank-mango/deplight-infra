# Rollback Trigger Lambda & API Gateway
# Terraform 설정 예시

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Variables
variable "github_token" {
  description = "GitHub Personal Access Token with workflow permissions"
  type        = string
  sensitive   = true
}

variable "github_repo_owner" {
  description = "GitHub repository owner"
  type        = string
  default     = "Softbank-mango"
}

variable "github_repo_name" {
  description = "GitHub repository name"
  type        = string
  default     = "deplight-infra"
}

variable "allowed_origins" {
  description = "Allowed CORS origins"
  type        = list(string)
  default     = ["https://your-ui-domain.com"]
}

# DynamoDB Table for Audit Logging
resource "aws_dynamodb_table" "rollback_audit_log" {
  name         = "rollback-audit-log"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "audit_id"

  attribute {
    name = "audit_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "environment"
    type = "S"
  }

  global_secondary_index {
    name            = "environment-timestamp-index"
    hash_key        = "environment"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  tags = {
    Name        = "Rollback Audit Log"
    Environment = "production"
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "rollback_lambda_role" {
  name = "rollback-trigger-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM Policy for Lambda
resource "aws_iam_role_policy" "rollback_lambda_policy" {
  name = "rollback-trigger-lambda-policy"
  role = aws_iam_role.rollback_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:GetItem"
        ]
        Resource = aws_dynamodb_table.rollback_audit_log.arn
      }
    ]
  })
}

# Lambda Function
resource "aws_lambda_function" "rollback_trigger" {
  filename      = "${path.module}/rollback-trigger.zip"
  function_name = "rollback-trigger"
  role          = aws_iam_role.rollback_lambda_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  memory_size   = 256

  environment {
    variables = {
      GITHUB_TOKEN      = var.github_token
      GITHUB_REPO_OWNER = var.github_repo_owner
      GITHUB_REPO_NAME  = var.github_repo_name
      AUDIT_TABLE_NAME  = aws_dynamodb_table.rollback_audit_log.name
    }
  }

  tags = {
    Name        = "Rollback Trigger"
    Environment = "production"
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "rollback_lambda_logs" {
  name              = "/aws/lambda/${aws_lambda_function.rollback_trigger.function_name}"
  retention_in_days = 14
}

# API Gateway (HTTP API)
resource "aws_apigatewayv2_api" "rollback_api" {
  name          = "rollback-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = var.allowed_origins
    allow_methods = ["POST", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization"]
    max_age       = 300
  }

  tags = {
    Name = "Rollback API"
  }
}

# API Gateway Stage
resource "aws_apigatewayv2_stage" "prod" {
  api_id      = aws_apigatewayv2_api.rollback_api.id
  name        = "prod"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_logs.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      resourcePath   = "$context.resourcePath"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
    })
  }
}

# CloudWatch Log Group for API Gateway
resource "aws_cloudwatch_log_group" "api_logs" {
  name              = "/aws/apigateway/rollback-api"
  retention_in_days = 14
}

# Lambda Integration
resource "aws_apigatewayv2_integration" "rollback_lambda" {
  api_id           = aws_apigatewayv2_api.rollback_api.id
  integration_type = "AWS_PROXY"
  integration_uri  = aws_lambda_function.rollback_trigger.invoke_arn

  payload_format_version = "2.0"
}

# API Route
resource "aws_apigatewayv2_route" "rollback_post" {
  api_id    = aws_apigatewayv2_api.rollback_api.id
  route_key = "POST /rollback"

  target = "integrations/${aws_apigatewayv2_integration.rollback_lambda.id}"
}

# Lambda Permission for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.rollback_trigger.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.rollback_api.execution_arn}/*/*"
}

# Outputs
output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = "${aws_apigatewayv2_api.rollback_api.api_endpoint}/prod/rollback"
}

output "lambda_function_name" {
  description = "Lambda function name"
  value       = aws_lambda_function.rollback_trigger.function_name
}

output "dynamodb_table_name" {
  description = "DynamoDB audit log table name"
  value       = aws_dynamodb_table.rollback_audit_log.name
}

output "api_gateway_id" {
  description = "API Gateway ID"
  value       = aws_apigatewayv2_api.rollback_api.id
}

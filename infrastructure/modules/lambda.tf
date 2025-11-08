# Lambda Function for AI Code Analyzer
resource "aws_lambda_function" "ai_analyzer" {
  function_name = "${var.app_name}-ai-analyzer"
  role          = var.use_existing_roles ? var.lambda_analyzer_role_arn : aws_iam_role.lambda_analyzer[0].arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 900  # 15 minutes for comprehensive analysis
  memory_size   = 1024

  filename         = "../../build/ai_analyzer.zip"
  source_code_hash = fileexists("../../build/ai_analyzer.zip") ? filebase64sha256("../../build/ai_analyzer.zip") : null

  environment {
    variables = {
      LETSUR_API_KEY_PARAM = var.letsur_api_key_param
      LETSUR_BASE_URL      = var.letsur_base_url
      LETSUR_MODEL         = var.letsur_model
      GARDEN_STATE_TABLE   = aws_dynamodb_table.garden_state.name
      AI_ANALYSIS_TABLE    = aws_dynamodb_table.ai_analysis.name
      DEPLOYMENT_TABLE     = aws_dynamodb_table.deployment_history.name
      S3_BUCKET            = var.artifacts_bucket_name
      ENVIRONMENT          = var.environment
    }
  }

  # Enable X-Ray tracing
  tracing_config {
    mode = var.enable_xray ? "Active" : "PassThrough"
  }

  # Reserved concurrent executions removed - account limit too low
  # reserved_concurrent_executions = 5

  tags = {
    Name = "${var.app_name}-ai-analyzer"
  }
}

# Lambda Function URL (for direct HTTP invocation from GitHub webhooks)
resource "aws_lambda_function_url" "ai_analyzer" {
  function_name      = aws_lambda_function.ai_analyzer.function_name
  authorization_type = "NONE"  # Use API Gateway or custom auth in production

  cors {
    allow_credentials = false
    allow_origins     = ["*"]
    allow_methods     = ["POST"]
    allow_headers     = ["*"]
    expose_headers    = ["*"]
    max_age           = 86400
  }
}

# EventBridge resources REMOVED - GitHub Actions now invokes Lambda directly
# Lambda is invoked via GitHub Actions workflows (.github/workflows/analyzer.yml)
# This provides better integration with the CI/CD pipeline

# Note: Lambda Function URL is still available for direct HTTP invocation if needed

# Dead Letter Queue for failed Lambda invocations
resource "aws_sqs_queue" "lambda_dlq" {
  name                      = "${var.app_name}-lambda-dlq"
  message_retention_seconds = 1209600  # 14 days
  receive_wait_time_seconds = 20

  tags = {
    Name = "${var.app_name}-lambda-dlq"
  }
}

# CloudWatch Log Group for Lambda
resource "aws_cloudwatch_log_group" "lambda_analyzer" {
  count             = 1
  name              = "/aws/lambda/${aws_lambda_function.ai_analyzer.function_name}"
  retention_in_days = 7

  lifecycle {
    prevent_destroy = false
  }

  tags = {
    Name = "${var.app_name}-lambda-logs"
  }
}

# Lambda Insights (enhanced monitoring)
# Commented out - use AWS-provided layer ARN in production:
# arn:aws:lambda:ap-northeast-2:580247275435:layer:LambdaInsightsExtension:latest
# resource "aws_lambda_layer_version" "lambda_insights" {
#   layer_name          = "LambdaInsightsExtension"
#   compatible_runtimes = ["python3.11"]
#   description = "Lambda Insights Extension"
# }

# CloudWatch Alarms for Lambda
resource "aws_cloudwatch_metric_alarm" "lambda_errors" {
  alarm_name          = "${var.app_name}-lambda-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "This alarm monitors Lambda function errors"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.ai_analyzer.function_name
  }

  tags = {
    Name = "${var.app_name}-lambda-errors-alarm"
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_duration" {
  alarm_name          = "${var.app_name}-lambda-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Average"
  threshold           = "300000"  # 5 minutes
  alarm_description   = "This alarm monitors Lambda function duration"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.ai_analyzer.function_name
  }

  tags = {
    Name = "${var.app_name}-lambda-duration-alarm"
  }
}

resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  alarm_name          = "${var.app_name}-lambda-throttles"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = "60"
  statistic           = "Sum"
  threshold           = "1"
  alarm_description   = "This alarm monitors Lambda function throttles"
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.ai_analyzer.function_name
  }

  tags = {
    Name = "${var.app_name}-lambda-throttles-alarm"
  }
}

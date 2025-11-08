data "aws_iam_policy_document" "ecs_execution_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_execution" {
  name               = "${var.project_name}-ecs-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_execution_assume.json

  tags = var.global_tags
}

resource "aws_iam_role_policy_attachment" "ecs_execution_default" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "ecs_execution_extra" {
  count  = var.task_execution_policy_json != "" ? 1 : 0
  name   = "${var.project_name}-ecs-execution-extra"
  role   = aws_iam_role.ecs_execution.id
  policy = var.task_execution_policy_json
}

data "aws_iam_policy_document" "ecs_task_assume" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "ecs_task" {
  name               = "${var.project_name}-ecs-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_task_assume.json

  tags = var.global_tags
}

resource "aws_iam_role_policy" "ecs_task_inline" {
  count  = var.task_role_policy_json != "" ? 1 : 0
  name   = "${var.project_name}-ecs-task-inline"
  role   = aws_iam_role.ecs_task.id
  policy = var.task_role_policy_json
}

resource "aws_iam_role_policy" "ecs_task_xray" {
  count = var.enable_xray ? 1 : 0

  name = "${var.project_name}-ecs-task-xray"
  role = aws_iam_role.ecs_task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords"
        ]
        Resource = "*"
      }
    ]
  })
}

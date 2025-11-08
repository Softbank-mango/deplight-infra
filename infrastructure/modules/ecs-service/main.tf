locals {
  common_tags = merge(
    var.tags,
    {
      Module = "ecs-service"
      Name   = var.name
    }
  )

  container_environment = [
    for env in var.environment : {
      name  = env.name
      value = env.value
    }
  ]

  xray_environment = var.enable_xray ? [
    {
      name  = "AWS_XRAY_DAEMON_ADDRESS"
      value = "127.0.0.1:2000"
    }
  ] : []

  main_container = {
    name      = var.name
    image     = var.container_image
    essential = true
    portMappings = [
      {
        containerPort = var.container_port
        hostPort      = var.container_port
        protocol      = "tcp"
      }
    ]
    environment = concat(local.container_environment, local.xray_environment)
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.this.name
        awslogs-region        = var.aws_region
        awslogs-stream-prefix = "ecs"
      }
    }
  }

  xray_container = var.enable_xray ? [
    {
      name      = "xray-daemon"
      image     = var.xray_daemon_image
      essential = false
      cpu       = var.xray_daemon_cpu
      memory    = var.xray_daemon_memory
      portMappings = [
        {
          containerPort = 2000
          protocol      = "udp"
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.this.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "xray"
        }
      }
    }
  ] : []

  task_containers = concat([local.main_container], local.xray_container)
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/ecs/${var.name}"
  retention_in_days = var.log_retention_in_days

  tags = local.common_tags
}

resource "aws_ecs_cluster" "this" {
  count = var.create_cluster ? 1 : 0

  name = var.cluster_name

  setting {
    name  = "containerInsights"
    value = var.enable_container_insights ? "enabled" : "disabled"
  }

  tags = local.common_tags
}

resource "aws_ecs_task_definition" "this" {
  family                   = var.name
  cpu                      = tostring(var.task_cpu)
  memory                   = tostring(var.task_memory)
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  execution_role_arn       = var.execution_role_arn
  task_role_arn            = var.task_role_arn

  container_definitions = jsonencode(local.task_containers)

  tags = local.common_tags
}

resource "aws_ecs_service" "this" {
  name                              = var.name
  cluster                           = var.create_cluster ? aws_ecs_cluster.this[0].id : var.cluster_arn
  task_definition                   = aws_ecs_task_definition.this.arn
  desired_count                     = var.desired_count
  launch_type                       = "FARGATE"
  platform_version                  = var.platform_version
  enable_execute_command            = var.enable_execute_command
  health_check_grace_period_seconds = var.health_check_grace_period_seconds

  lifecycle {
    ignore_changes = [
      desired_count,
      task_definition,
      load_balancer
    ]
  }

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = var.security_group_ids
    assign_public_ip = var.assign_public_ip
  }

  dynamic "load_balancer" {
    for_each = var.target_group_arn != null ? [var.target_group_arn] : []
    content {
      target_group_arn = load_balancer.value
      container_name   = var.name
      container_port   = var.container_port
    }
  }

  deployment_controller {
    type = var.use_codedeploy ? "CODE_DEPLOY" : "ECS"
  }

  propagate_tags = "SERVICE"
  tags           = local.common_tags

  depends_on = [
    aws_cloudwatch_log_group.this
  ]
}

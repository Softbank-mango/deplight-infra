terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

locals {
  ecs_env = [
    for key, value in var.environment_variables :
    {
      name  = key
      value = value
    }
  ]
}

module "network" {
  source = "./modules/network-baseline"

  name                = "${var.project_name}-network"
  vpc_cidr            = var.vpc_cidr
  public_subnet_cidrs = var.public_subnet_cidrs
  availability_zones  = var.availability_zones
  tags                = var.global_tags
}

module "alb" {
  source = "./modules/alb-bluegreen"

  name                     = "${var.project_name}-alb"
  vpc_id                   = module.network.vpc_id
  subnet_ids               = module.network.public_subnet_ids
  security_group_ids       = [aws_security_group.alb.id]
  target_port              = var.container_port
  health_check_path        = var.health_check_path
  production_listener_port = var.production_listener_port
  test_listener_port       = var.test_listener_port
  tags                     = var.global_tags
}

module "ecs_service" {
  source = "./modules/ecs-service"

  name                   = "${var.project_name}-service"
  aws_region             = var.aws_region
  cluster_name           = "${var.project_name}-cluster"
  create_cluster         = true
  execution_role_arn     = aws_iam_role.ecs_execution.arn
  task_role_arn          = aws_iam_role.ecs_task.arn
  container_image        = var.container_image
  container_port         = var.container_port
  desired_count          = var.desired_count
  task_cpu               = var.task_cpu
  task_memory            = var.task_memory
  subnet_ids             = module.network.public_subnet_ids
  security_group_ids     = [aws_security_group.ecs.id]
  assign_public_ip       = true
  target_group_arn       = module.alb.blue_target_group_arn
  environment            = local.ecs_env
  log_retention_in_days  = var.log_retention_in_days
  enable_execute_command = var.enable_execute_command
  enable_xray            = var.enable_xray
  xray_daemon_image      = var.xray_daemon_image
  xray_daemon_cpu        = var.xray_daemon_cpu
  xray_daemon_memory     = var.xray_daemon_memory
  tags                   = var.global_tags
  use_codedeploy         = true
}

module "codedeploy" {
  source = "./modules/codedeploy-bluegreen"

  name                             = var.project_name
  cluster_name                     = module.ecs_service.cluster_name
  service_name                     = module.ecs_service.service_name
  production_listener_arn          = module.alb.production_listener_arn
  test_listener_arn                = module.alb.test_listener_arn
  blue_target_group_name           = module.alb.blue_target_group_name
  green_target_group_name          = module.alb.green_target_group_name
  deployment_config_name           = var.deployment_config_name
  termination_wait_time_in_minutes = var.termination_wait_time_in_minutes
  ready_wait_time_in_minutes       = var.ready_wait_time_in_minutes
  action_on_timeout                = var.action_on_timeout
  tags                             = var.global_tags
}

module "github_oidc" {
  source = "./modules/iam-github-oidc"

  github_org       = var.github_org
  github_repo      = var.github_repo
  role_name        = var.github_oidc_role_name
  allowed_subjects = var.github_allowed_subjects
}

module "observability" {
  source = "./modules/observability-suite"

  environment                 = var.environment_name
  service_name                = module.ecs_service.service_name
  cluster_name                = module.ecs_service.cluster_name
  region                      = var.aws_region
  alb_target_group_arn_suffix = module.alb.blue_target_group_arn_suffix
  enable_alb_metrics          = true

  log_group_names          = []
  log_retention_in_days    = 30
  xray_sampling_enabled    = true
  xray_fixed_rate          = 0.1
  xray_reservoir_size      = 1
  alarm_topic_arn          = null
  cpu_high_threshold       = 80
  memory_high_threshold    = 80
  alb_5xx_threshold        = 5
  alb_latency_threshold_ms = 1500

  tags = var.global_tags
}

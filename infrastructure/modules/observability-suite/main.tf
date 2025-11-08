locals {
  name_prefix    = "${var.environment}-${var.service_name}"
  dashboard_name = "${local.name_prefix}-ecs-observability"
  alarm_actions  = var.alarm_topic_arn == null ? [] : [var.alarm_topic_arn]
  alb_enabled    = var.enable_alb_metrics && var.alb_target_group_arn_suffix != null && var.alb_target_group_arn_suffix != ""
  xray_rule_name = lower("${substr(var.environment, 0, 3)}-${substr(var.service_name, 0, 8)}-ecs")

  common_tags = merge(
    {
      Environment = var.environment
      Service     = var.service_name
      Module      = "observability-suite"
    },
    var.tags,
  )

  dashboard_body = templatefile("${path.module}/templates/ecs_dashboard.json.tpl", {
    dashboard_title  = "${upper(var.environment)} ${var.service_name} ECS"
    region           = var.region
    cluster_name     = var.cluster_name
    service_name     = var.service_name
    include_alb      = local.alb_enabled
    target_group_dim = var.alb_target_group_arn_suffix
  })
}

resource "aws_cloudwatch_dashboard" "ecs" {
  dashboard_name = local.dashboard_name
  dashboard_body = local.dashboard_body
}

resource "aws_cloudwatch_log_group" "managed" {
  for_each = { for name in var.log_group_names : name => name }

  name              = each.value
  retention_in_days = var.log_retention_in_days
  tags              = local.common_tags
}

resource "aws_xray_sampling_rule" "this" {
  count = var.xray_sampling_enabled ? 1 : 0

  rule_name      = local.xray_rule_name
  priority       = 5000
  fixed_rate     = var.xray_fixed_rate
  reservoir_size = var.xray_reservoir_size
  version        = 1

  resource_arn = "*"
  service_name = var.service_name
  service_type = "AWS::ECS::Service"
  host         = "*"
  http_method  = "*"
  url_path     = "*"

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "${local.name_prefix}-cpu-high"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = var.cpu_high_threshold
  treat_missing_data  = "notBreaching"
  alarm_description   = "ECS service CPU utilization breached ${var.cpu_high_threshold}%."
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions

  dimensions = {
    ClusterName = var.cluster_name
    ServiceName = var.service_name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "memory_high" {
  alarm_name          = "${local.name_prefix}-memory-high"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 2
  datapoints_to_alarm = 2
  metric_name         = "MemoryUtilization"
  namespace           = "AWS/ECS"
  period              = 60
  statistic           = "Average"
  threshold           = var.memory_high_threshold
  treat_missing_data  = "notBreaching"
  alarm_description   = "ECS service memory utilization breached ${var.memory_high_threshold}%."
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions

  dimensions = {
    ClusterName = var.cluster_name
    ServiceName = var.service_name
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "alb_5xx" {
  count = var.enable_alb_metrics ? 1 : 0

  alarm_name          = "${local.name_prefix}-alb-5xx"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Sum"
  threshold           = var.alb_5xx_threshold
  treat_missing_data  = "notBreaching"
  alarm_description   = "Target group reported >= ${var.alb_5xx_threshold} 5XX responses."
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions

  dimensions = {
    TargetGroup = var.alb_target_group_arn_suffix
  }

  tags = local.common_tags
}

resource "aws_cloudwatch_metric_alarm" "alb_latency" {
  count = var.enable_alb_metrics ? 1 : 0

  alarm_name          = "${local.name_prefix}-alb-latency"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods  = 1
  datapoints_to_alarm = 1
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  extended_statistic  = "p99"
  threshold           = var.alb_latency_threshold_ms / 1000
  treat_missing_data  = "notBreaching"
  alarm_description   = "P99 target response time exceeded ${var.alb_latency_threshold_ms}ms."
  alarm_actions       = local.alarm_actions
  ok_actions          = local.alarm_actions

  dimensions = {
    TargetGroup = var.alb_target_group_arn_suffix
  }

  tags = local.common_tags
}

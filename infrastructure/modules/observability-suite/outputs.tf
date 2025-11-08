output "dashboard_name" {
  description = "Name of the CloudWatch dashboard for the ECS service."
  value       = aws_cloudwatch_dashboard.ecs.dashboard_name
}

output "dashboard_body" {
  description = "Rendered JSON body for the ECS dashboard."
  value       = local.dashboard_body
}

output "alarm_arns" {
  description = "Map of CloudWatch alarm ARNs keyed by alarm purpose."
  value = {
    cpu_high    = aws_cloudwatch_metric_alarm.cpu_high.arn
    memory_high = aws_cloudwatch_metric_alarm.memory_high.arn
    alb_5xx     = local.alb_enabled ? aws_cloudwatch_metric_alarm.alb_5xx[0].arn : null
    alb_latency = local.alb_enabled ? aws_cloudwatch_metric_alarm.alb_latency[0].arn : null
  }
}

output "xray_sampling_rule_arn" {
  description = "ARN of the AWS X-Ray sampling rule when enabled."
  value       = var.xray_sampling_enabled ? aws_xray_sampling_rule.this[0].arn : null
}

output "cluster_id" {
  description = "ID of the ECS cluster."
  value       = var.create_cluster ? try(aws_ecs_cluster.this[0].id, null) : var.cluster_arn
}

output "cluster_name" {
  description = "Name of the ECS cluster."
  value       = var.cluster_name
}

output "cluster_arn" {
  description = "ARN of the ECS cluster."
  value       = var.create_cluster ? try(aws_ecs_cluster.this[0].arn, null) : var.cluster_arn
}

output "service_name" {
  description = "Name of the ECS service."
  value       = aws_ecs_service.this.name
}

output "service_arn" {
  description = "ARN of the ECS service."
  value       = aws_ecs_service.this.arn
}

output "task_definition_arn" {
  description = "ARN of the task definition used by the service."
  value       = aws_ecs_task_definition.this.arn
}

output "log_group_name" {
  description = "CloudWatch log group name for the service."
  value       = aws_cloudwatch_log_group.this.name
}

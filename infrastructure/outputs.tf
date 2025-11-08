output "vpc_id" {
  description = "ID of the hackathon VPC."
  value       = module.network.vpc_id
}

output "public_subnet_ids" {
  description = "Public subnet IDs for ECS/ALB."
  value       = module.network.public_subnet_ids
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer."
  value       = module.alb.alb_dns_name
}

output "ecs_service_name" {
  description = "Name of the ECS service."
  value       = module.ecs_service.service_name
}

output "ecs_task_definition" {
  description = "ECS task definition ARN."
  value       = module.ecs_service.task_definition_arn
}

output "codedeploy_deployment_group" {
  description = "Name of the CodeDeploy deployment group."
  value       = module.codedeploy.codedeploy_deployment_group_name
}

output "container_image" {
  description = "Container image URI deployed to ECS (includes image tag)."
  value       = var.container_image
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster."
  value       = module.ecs_service.cluster_name
}

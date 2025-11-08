variable "aws_region" {
  type        = string
  description = "AWS region for all resources."
  default     = "ap-northeast-2"
}

variable "project_name" {
  type        = string
  description = "Prefix used when naming infrastructure resources."
  default     = "delightful-deploy"
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for the hackathon VPC."
  default     = "10.20.0.0/16"
}

variable "public_subnet_cidrs" {
  type        = list(string)
  description = "Public subnet CIDRs (must align with availability_zones)."
  default     = ["10.20.0.0/20", "10.20.16.0/20"]
}

variable "availability_zones" {
  type        = list(string)
  description = "Availability zones for the subnets."
  default     = ["ap-northeast-2a", "ap-northeast-2c"]
}

variable "alb_ingress_cidrs" {
  type        = list(string)
  description = "CIDR blocks allowed to reach the ALB."
  default     = ["0.0.0.0/0"]
}

variable "task_execution_policy_json" {
  type        = string
  description = "JSON policy for the ECS execution role (optional override)."
  default     = ""
}

variable "task_role_policy_json" {
  type        = string
  description = "JSON policy for the ECS task role."
  default     = ""
}

variable "container_image" {
  type        = string
  description = "Container image URI deployed to ECS."
  default     = "513348493870.dkr.ecr.ap-northeast-2.amazonaws.com/delightful-app:latest"
}

variable "container_port" {
  type        = number
  description = "Container/application port exposed via ALB."
  default     = 80
}

variable "desired_count" {
  type        = number
  description = "Desired ECS task count."
  default     = 1
}

variable "task_cpu" {
  type        = number
  description = "Fargate CPU units."
  default     = 256
}

variable "task_memory" {
  type        = number
  description = "Fargate memory (MB)."
  default     = 512
}

variable "environment_variables" {
  type        = map(string)
  description = "Environment variables injected into the container."
  default = {
    APP_ENV = "dev"
  }
}

variable "log_retention_in_days" {
  type        = number
  description = "CloudWatch log retention for ECS service."
  default     = 14
}

variable "enable_execute_command" {
  type        = bool
  description = "Enable ECS Exec in the service."
  default     = false
}

variable "enable_xray" {
  type        = bool
  description = "Enable AWS X-Ray daemon sidecar in the ECS task."
  default     = true
}

variable "xray_daemon_image" {
  type        = string
  description = "Container image used for the X-Ray daemon."
  default     = "amazon/aws-xray-daemon:3.3.11"
}

variable "xray_daemon_cpu" {
  type        = number
  description = "CPU units reserved for the X-Ray daemon."
  default     = 64
}

variable "xray_daemon_memory" {
  type        = number
  description = "Memory (MB) reserved for the X-Ray daemon."
  default     = 128
}

variable "health_check_path" {
  type        = string
  description = "ALB target group health check path."
  default     = "/"
}

variable "production_listener_port" {
  type        = number
  description = "Port for the production ALB listener."
  default     = 80
}

variable "test_listener_port" {
  type        = number
  description = "Port for the test ALB listener."
  default     = 9001
}

variable "deployment_config_name" {
  type        = string
  description = "CodeDeploy deployment config identifier."
  default     = "CodeDeployDefault.ECSAllAtOnce"
}

variable "termination_wait_time_in_minutes" {
  type        = number
  description = "Minutes to wait before terminating the old task set."
  default     = 5
}

variable "ready_wait_time_in_minutes" {
  type        = number
  description = "Minutes CodeDeploy waits before routing production traffic to the new task set."
  default     = 0
}

variable "action_on_timeout" {
  type        = string
  description = "Action CodeDeploy takes if deployment readiness times out."
  default     = "CONTINUE_DEPLOYMENT"
}

variable "global_tags" {
  type        = map(string)
  description = "Tags applied to all modules."
  default = {
    Project = "delightful-deploy"
    Owner   = "hackathon"
  }
}

variable "github_org" {
  type        = string
  description = "GitHub organization for the deployment repository."
  default     = "Softbank-mango"
}

variable "github_repo" {
  type        = string
  description = "GitHub repository name."
  default     = "deplight-platform"
}

variable "github_oidc_role_name" {
  type        = string
  description = "IAM role name for GitHub Actions OIDC."
  default     = "github-actions-oidc-validation"
}

variable "github_allowed_subjects" {
  type        = list(string)
  description = "Additional GitHub OIDC subject patterns allowed to assume the role."
  default     = []
}

variable "environment_name" {
  type        = string
  description = "Environment identifier used for cross-cutting resources (e.g., observability)."
  default     = "dev"
}

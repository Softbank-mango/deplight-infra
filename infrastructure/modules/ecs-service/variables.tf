variable "name" {
  type        = string
  description = "Service name used for ECS resources."
}

variable "aws_region" {
  type        = string
  description = "AWS region for log configuration."
}

variable "cluster_name" {
  type        = string
  description = "Name of the ECS cluster to create or target."
}

variable "create_cluster" {
  type        = bool
  description = "Whether this module should create an ECS cluster."
  default     = true
}

variable "cluster_arn" {
  type        = string
  description = "Existing ECS cluster ARN (used when create_cluster is false)."
  default     = ""
}

variable "execution_role_arn" {
  type        = string
  description = "IAM execution role ARN for the task definition."
}

variable "task_role_arn" {
  type        = string
  description = "IAM task role ARN for the task definition."
}

variable "container_image" {
  type        = string
  description = "Container image URI deployed by the service."
}

variable "container_port" {
  type        = number
  description = "Container port exposed by the task."
  default     = 80
}

variable "desired_count" {
  type        = number
  description = "Desired number of service tasks."
  default     = 1
}

variable "task_cpu" {
  type        = number
  description = "Fargate CPU units (e.g., 256)."
  default     = 256
}

variable "task_memory" {
  type        = number
  description = "Fargate memory (MB)."
  default     = 512
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnets used by the ECS service network configuration."
}

variable "security_group_ids" {
  type        = list(string)
  description = "Security groups attached to the ECS service."
}

variable "assign_public_ip" {
  type        = bool
  description = "Whether to assign public IPs to service tasks."
  default     = false
}

variable "target_group_arn" {
  type        = string
  description = "Optional ALB/NLB target group ARN for the service."
  default     = null
}

variable "enable_container_insights" {
  type        = bool
  description = "Enable ECS container insights on the cluster."
  default     = true
}

variable "enable_execute_command" {
  type        = bool
  description = "Enable ECS Exec command on the service."
  default     = false
}

variable "enable_xray" {
  type        = bool
  description = "Inject the AWS X-Ray daemon sidecar."
  default     = false
}

variable "xray_daemon_image" {
  type        = string
  description = "Container image for the X-Ray daemon."
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

variable "health_check_grace_period_seconds" {
  type        = number
  description = "Seconds to ignore health checks after deployment."
  default     = 60
}

variable "platform_version" {
  type        = string
  description = "Fargate platform version."
  default     = "1.4.0"
}

variable "use_codedeploy" {
  type        = bool
  description = "Whether the service deployment controller should use CodeDeploy."
  default     = false
}

variable "environment" {
  type = list(object({
    name  = string
    value = string
  }))
  description = "Container environment variables."
  default     = []
}

variable "log_retention_in_days" {
  type        = number
  description = "CloudWatch Logs retention period."
  default     = 14
}

variable "tags" {
  type        = map(string)
  description = "Common tags applied to ECS resources."
  default     = {}
}

variable "environment" {
  type        = string
  description = "Environment label (e.g., dev, staging) applied to observability resources."
}

variable "service_name" {
  type        = string
  description = "Primary ECS service name used for dashboard dimensions."
}

variable "region" {
  type        = string
  description = "AWS region for CloudWatch widgets."
}

variable "cluster_name" {
  type        = string
  description = "ECS cluster name for metric dimensions."
}

variable "alb_target_group_arn_suffix" {
  type        = string
  description = "Optional target group ARN suffix (targetgroup/...) used for ALB metrics."
  default     = null
}

variable "enable_alb_metrics" {
  type        = bool
  description = "Force-enable ALB widgets/alarms when target group info is known."
  default     = false
}

variable "log_group_names" {
  type        = list(string)
  description = "Log group names that should share the configured retention policy."
  default     = []
}

variable "log_retention_in_days" {
  type        = number
  description = "Retention period applied to each managed log group."
  default     = 30
}

variable "xray_sampling_enabled" {
  type        = bool
  description = "Toggle creation of the AWS X-Ray sampling rule."
  default     = false
}

variable "xray_fixed_rate" {
  type        = number
  description = "Fixed sampling rate (0-1) when the sampling rule is enabled."
  default     = 0.1
}

variable "xray_reservoir_size" {
  type        = number
  description = "Requests per second to sample before the fixed rate applies."
  default     = 1
}

variable "alarm_topic_arn" {
  type        = string
  description = "SNS topic ARN for alarm/OK actions; alarms emit no notifications when unset."
  default     = null
}

variable "cpu_high_threshold" {
  type        = number
  description = "CPU utilization percentage that should raise an alarm."
  default     = 80
}

variable "memory_high_threshold" {
  type        = number
  description = "Memory utilization percentage that should raise an alarm."
  default     = 80
}

variable "alb_5xx_threshold" {
  type        = number
  description = "5XX error count threshold for the ALB target group alarm."
  default     = 5
}

variable "alb_latency_threshold_ms" {
  type        = number
  description = "Target response latency (milliseconds) threshold for the ALB alarm."
  default     = 1500
}

variable "tags" {
  type        = map(string)
  description = "Additional tags applied to observability resources."
  default     = {}
}

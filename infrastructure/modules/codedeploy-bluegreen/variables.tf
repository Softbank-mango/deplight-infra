variable "name" {
  type        = string
  description = "Name prefix for CodeDeploy resources."
}

variable "cluster_name" {
  type        = string
  description = "ECS cluster name targeted by the deployment group."
}

variable "service_name" {
  type        = string
  description = "ECS service name targeted by the deployment group."
}

variable "production_listener_arn" {
  type        = string
  description = "ARN of the production ALB listener."
}

variable "test_listener_arn" {
  type        = string
  description = "ARN of the test ALB listener for blue/green."
}

variable "blue_target_group_name" {
  type        = string
  description = "Name of the blue target group."
}

variable "green_target_group_name" {
  type        = string
  description = "Name of the green target group."
}

variable "deployment_config_name" {
  type        = string
  description = "CodeDeploy deployment config to use (e.g., CodeDeployDefault.ECSLinear10PercentEvery1Minutes)."
  default     = "CodeDeployDefault.ECSAllAtOnce"
}

variable "termination_wait_time_in_minutes" {
  type        = number
  description = "Minutes to wait before terminating the old task set."
  default     = 5
}

variable "ready_wait_time_in_minutes" {
  type        = number
  description = "Minutes CodeDeploy waits for the new task set before routing production traffic."
  default     = 0
}

variable "action_on_timeout" {
  type        = string
  description = "Action when new deployment is not ready in time (CONTINUE or STOP_DEPLOYMENT)."
  default     = "CONTINUE"
}

variable "tags" {
  type        = map(string)
  description = "Common tags applied to CodeDeploy resources."
  default     = {}
}

variable "name" {
  type        = string
  description = "Name prefix for ALB and target groups."
}

variable "vpc_id" {
  type        = string
  description = "VPC ID where the ALB and target groups reside."
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnets for the ALB (usually public)."
}

variable "security_group_ids" {
  type        = list(string)
  description = "Security groups to attach to the ALB."
}

variable "target_port" {
  type        = number
  description = "Port for target groups."
  default     = 80
}

variable "health_check_path" {
  type        = string
  description = "Health check path for target groups."
  default     = "/"
}

variable "production_listener_port" {
  type        = number
  description = "Port for the production listener."
  default     = 80
}

variable "test_listener_port" {
  type        = number
  description = "Port for the test listener used in blue/green deployments."
  default     = 9001
}

variable "tags" {
  type        = map(string)
  description = "Common tags applied to ALB resources."
  default     = {}
}

variable "name" {
  type        = string
  description = "Name prefix applied to network resources."
}

variable "vpc_cidr" {
  type        = string
  description = "CIDR block for the VPC."
}

variable "public_subnet_cidrs" {
  type        = list(string)
  description = "CIDR blocks for each public subnet."
}

variable "availability_zones" {
  type        = list(string)
  description = "Availability zones corresponding to each public subnet."
}

variable "tags" {
  type        = map(string)
  description = "Common tags applied to all network resources."
  default     = {}
}

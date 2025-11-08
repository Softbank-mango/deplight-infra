variable "github_org" {
  type        = string
  description = "GitHub organization that owns the repository whose workflow will assume this role."
}

variable "github_repo" {
  type        = string
  description = "GitHub repository whose workflow will assume this role."
}

variable "allowed_subjects" {
  type        = list(string)
  description = "Optional list of additional GitHub OIDC sub patterns (e.g., repo:org/repo:ref:refs/heads/main). Defaults to the standard branch wildcard."
  default     = []
}

variable "role_name" {
  type        = string
  description = "Name to assign to the IAM role GitHub Actions will assume."
}

variable "github_oidc_audience" {
  type        = string
  description = "Expected audience value from GitHub's OIDC token. Usually sts.amazonaws.com."
  default     = "sts.amazonaws.com"
}

variable "max_session_duration" {
  type        = number
  description = "Maximum session duration (in seconds) for the IAM role."
  default     = 3600
}

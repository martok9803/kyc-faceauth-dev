variable "aws_region" {
  description = "Region for bootstrap resources"
  type        = string
  default     = "eu-central-1"
}

variable "project" {
  description = "Project prefix"
  type        = string
  default     = "kyc"
}

variable "env" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "github_org" {
  description = "GitHub org or username that owns the repo"
  type        = string
}

variable "github_repo" {
  description = "Repository name"
  type        = string
}

variable "allowed_branches" {
  description = "Branches that may assume the deploy role"
  type        = list(string)
  default     = ["refs/heads/main"]
}

variable "tags" {
  description = "Common tags"
  type        = map(string)
  default = {
    Environment = "dev"
    Project     = "kyc"
    Owner       = "martin"
  }
}

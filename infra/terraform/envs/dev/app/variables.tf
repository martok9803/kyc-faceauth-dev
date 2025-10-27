variable "aws_region" {
  type        = string
  default     = "eu-central-1"
  description = "AWS region"
}

variable "project" {
  type    = string
  default = "kyc"
}

variable "env" {
  type    = string
  default = "dev"
}

variable "tags" {
  type = map(string)
  default = {
    Environment = "dev"
    Project     = "kyc"
    Owner       = "martok9803"
  }
}

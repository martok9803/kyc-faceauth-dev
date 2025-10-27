terraform {
  required_version = ">= 1.7.0"

  backend "s3" {} # lets you pass -backend-config flags

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 6.0.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = ">= 2.5.0"
    }
  }
}

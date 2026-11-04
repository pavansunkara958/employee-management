terraform {
  required_version = ">= 1.10"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }

  backend "s3" {
    bucket       = "emp-tfstate-271376212032"
    key          = "employee-mgmt/dev/terraform.tfstate"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true # S3-native state locking (Terraform 1.10+)
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = { Project = var.project, Env = var.env, ManagedBy = "terraform" }
  }
}

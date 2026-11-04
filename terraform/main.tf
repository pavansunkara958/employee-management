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

locals {
  name     = "${var.project}-${var.env}" # employee-mgmt-dev
  vpc_cidr = "10.0.0.0/16"
}

module "vpc" {
  source = "./modules/vpc"
  name   = local.name
  cidr   = local.vpc_cidr
}

module "security" {
  source           = "./modules/security"
  name             = local.name
  vpc_id           = module.vpc.vpc_id
  vpc_cidr         = local.vpc_cidr
  app_ingress_cidr = var.app_ingress_cidr
}

module "rds" {
  source             = "./modules/rds"
  name               = local.name
  private_subnet_ids = module.vpc.private_subnet_ids
  rds_sg_id          = module.security.rds_sg_id
}

module "ecr" {
  source = "./modules/ecr"
  name   = var.project # repository: employee-mgmt
}

module "ec2" {
  source           = "./modules/ec2"
  name             = local.name
  region           = var.aws_region
  instance_type    = var.instance_type
  public_subnet_id = module.vpc.public_subnet_id
  ec2_sg_id        = module.security.ec2_sg_id
  ecr_repo_url     = module.ecr.repository_url
  ecr_repo_arn     = module.ecr.repository_arn
  db_secret_arn    = module.rds.secret_arn
  db_host          = module.rds.address
  db_name          = module.rds.db_name
}

module "github_oidc" {
  source       = "./modules/github-oidc"
  name         = local.name
  region       = var.aws_region
  github_repo  = var.github_repo
  ecr_repo_arn = module.ecr.repository_arn
  instance_arn = module.ec2.instance_arn
}

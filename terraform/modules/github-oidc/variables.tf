variable "name" {
  type = string
}

variable "region" {
  type = string
}

variable "github_repo" {
  type        = string
  description = "owner/repo"
}

variable "ecr_repo_arn" {
  type = string
}

variable "instance_arn" {
  type = string
}

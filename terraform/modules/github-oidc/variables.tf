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

variable "github_repo_ids" {
  type        = string
  description = "owner@id/repo@id, as GitHub sends it in the OIDC sub claim"
}

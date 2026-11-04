variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "project" {
  type    = string
  default = "employee-mgmt"
}

variable "env" {
  type    = string
  default = "dev"
}

variable "instance_type" {
  type    = string
  default = "t3.micro"
}

variable "github_repo" {
  type        = string
  description = "owner/repo allowed to assume the pipeline role"
}

variable "app_ingress_cidr" {
  type        = string
  description = "Who may reach port 8080: 0.0.0.0/0 for the demo, or your.ip/32"
  default     = "0.0.0.0/0"
}

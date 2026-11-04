output "ec2_public_ip" {
  value = module.ec2.public_ip
}

output "ec2_instance_id" {
  value = module.ec2.instance_id
}

output "ec2_name_tag" {
  value = module.ec2.name_tag
}

output "app_url" {
  value = "http://${module.ec2.public_ip}:8080"
}

output "rds_endpoint" {
  value = module.rds.address
}

output "ecr_repository_url" {
  value = module.ecr.repository_url
}

output "db_secret_arn" {
  value = module.rds.secret_arn
}

output "github_actions_role_arn" {
  value = module.github_oidc.role_arn
}

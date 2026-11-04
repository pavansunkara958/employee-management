resource "aws_db_subnet_group" "this" {
  name       = "${var.name}-db-subnets"
  subnet_ids = var.private_subnet_ids
  tags       = { Name = "${var.name}-db-subnets" }
}

resource "aws_db_instance" "this" {
  identifier     = "${var.name}-db"
  engine         = "postgres"
  engine_version = "16"
  instance_class = "db.t3.micro"

  allocated_storage = 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_name                     = "employees"
  username                    = "appuser"
  manage_master_user_password = true # RDS generates the password and stores it in Secrets Manager

  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = [var.rds_sg_id]
  publicly_accessible    = false
  multi_az               = false

  backup_retention_period    = 1     # set to 0 if the free plan rejects it
  skip_final_snapshot        = true  # practice environment
  deletion_protection        = false # practice environment — destroyed every session
  auto_minor_version_upgrade = true
  apply_immediately          = true

  tags = { Name = "${var.name}-db" }
}

output "address" {
  value = aws_db_instance.this.address
}

output "db_name" {
  value = aws_db_instance.this.db_name
}

output "secret_arn" {
  value = aws_db_instance.this.master_user_secret[0].secret_arn
}

resource "aws_security_group" "ec2" {
  name        = "${var.name}-ec2-sg"
  description = "App server"
  vpc_id      = var.vpc_id

  # Accepted risk: demo app must be reachable from browsers; no load balancer by design.
  #trivy:ignore:AVD-AWS-0107
  ingress {
    description = "App HTTP"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = [var.app_ingress_cidr]
  }

  # Accepted risk: HTTPS out to ECR, SSM, Secrets Manager, CloudWatch and dnf repos. No NAT/VPC endpoints (cost).
  #trivy:ignore:AVD-AWS-0104
  egress {
    description = "HTTPS to AWS APIs and package repos"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "PostgreSQL to RDS inside the VPC"
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = [var.vpc_cidr]
  }

  tags = { Name = "${var.name}-ec2-sg" }
}

resource "aws_security_group" "rds" {
  name        = "${var.name}-rds-sg"
  description = "Database - app server only"
  vpc_id      = var.vpc_id

  ingress {
    description     = "PostgreSQL from the app server only"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }

  tags = { Name = "${var.name}-rds-sg" }
}

output "ec2_sg_id" {
  value = aws_security_group.ec2.id
}

output "rds_sg_id" {
  value = aws_security_group.rds.id
}

# S0: security groups and rules.
#
# Decision point: who may reach the app (ingress scope)? Record it in decisions/.
# Traffic between hosts (ports in contracts/runtime.yaml):
#   app -> platform  MLflow (5000)
#   app, platform -> llm  chat (8080) and embeddings (8081)
#   app, platform -> rds  Postgres (5432)
# There is no SSH in this lab: use SSM Session Manager for a shell and port forwarding for UIs.

resource "aws_security_group" "app" {
  name        = "lab-app"
  description = "App host: Traefik on port 80"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "Traefik HTTP ingress"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = var.ingress_cidrs
  }

  egress {
    description      = "All outbound"
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = { Name = "lab-app" }
}

resource "aws_security_group" "platform" {
  name        = "lab-platform"
  description = "Platform host: Dagster (3000), MLflow (5000)"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "MLflow from app host"
    from_port       = 5000
    to_port         = 5000
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  ingress {
    description = "Self internal platform"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }

  egress {
    description      = "All outbound"
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = { Name = "lab-platform" }
}

resource "aws_security_group" "llm" {
  name        = "lab-llm"
  description = "LLM host: chat (8080) and embed (8081)"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "LLM chat from app and platform"
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id, aws_security_group.platform.id]
  }

  ingress {
    description     = "LLM embed from app and platform"
    from_port       = 8081
    to_port         = 8081
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id, aws_security_group.platform.id]
  }

  ingress {
    description = "Self internal LLM"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    self        = true
  }

  egress {
    description      = "All outbound"
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = { Name = "lab-llm" }
}

resource "aws_security_group" "rds" {
  name        = "lab-rds"
  description = "Postgres RDS for platform and app"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "Postgres from platform host"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.platform.id]
  }

  ingress {
    description     = "Postgres from app host"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  egress {
    description      = "All outbound"
    from_port        = 0
    to_port          = 0
    protocol         = "-1"
    cidr_blocks      = ["0.0.0.0/0"]
    ipv6_cidr_blocks = ["::/0"]
  }

  tags = { Name = "lab-rds" }
}

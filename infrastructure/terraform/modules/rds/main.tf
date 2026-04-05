variable "identifier"     { type = string }
variable "vpc_id"         { type = string }
variable "subnet_ids"     { type = list(string) }
variable "db_name"        { type = string }
variable "db_username"    { type = string }
variable "instance_class" { type = string; default = "db.t4g.medium" }
variable "multi_az"       { type = bool; default = false }
variable "tags"           { type = map(string); default = {} }

resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "db_password" {
  name = "${var.identifier}-password"
  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "db_password" {
  secret_id     = aws_secretsmanager_secret.db_password.id
  secret_string = random_password.db.result
}

resource "aws_db_subnet_group" "this" {
  name       = "${var.identifier}-subnet-group"
  subnet_ids = var.subnet_ids
  tags       = var.tags
}

resource "aws_security_group" "rds" {
  name   = "${var.identifier}-sg"
  vpc_id = var.vpc_id

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = var.tags
}

resource "aws_db_instance" "this" {
  identifier              = var.identifier
  engine                  = "postgres"
  engine_version          = "16.2"
  instance_class          = var.instance_class
  db_name                 = var.db_name
  username                = var.db_username
  password                = random_password.db.result
  db_subnet_group_name    = aws_db_subnet_group.this.name
  vpc_security_group_ids  = [aws_security_group.rds.id]
  multi_az                = var.multi_az
  storage_type            = "gp3"
  allocated_storage       = 100
  max_allocated_storage   = 1000
  backup_retention_period = 7
  deletion_protection     = true
  skip_final_snapshot     = false
  final_snapshot_identifier = "${var.identifier}-final"
  enabled_cloudwatch_logs_exports = ["postgresql"]
  tags = var.tags
}

output "endpoint"    { value = aws_db_instance.this.endpoint }
output "db_name"     { value = aws_db_instance.this.db_name }
output "secret_arn"  { value = aws_secretsmanager_secret.db_password.arn }

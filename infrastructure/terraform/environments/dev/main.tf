terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = { source = "hashicorp/aws"; version = "~> 5.0" }
  }
  # Dev uses local state — no remote backend
}

provider "aws" { region = var.aws_region }

variable "aws_region" { default = "us-east-1" }
variable "vpc_id"     { type = string; default = "vpc-dev00000" }
variable "subnet_ids" { type = list(string); default = ["subnet-dev0001", "subnet-dev0002"] }

locals {
  name = "security-fabric-dev"
  tags = { Project = "security-fabric", Environment = "dev", ManagedBy = "terraform" }
}

module "eks" {
  source             = "../../modules/eks"
  cluster_name       = local.name
  region             = var.aws_region
  vpc_id             = var.vpc_id
  subnet_ids         = var.subnet_ids
  node_instance_type = "t3.large"
  desired_capacity   = 2
  min_size           = 1
  max_size           = 5
  tags               = local.tags
}

module "rds" {
  source         = "../../modules/rds"
  identifier     = "${local.name}-db"
  vpc_id         = var.vpc_id
  subnet_ids     = var.subnet_ids
  db_name        = "security_fabric"
  db_username    = "fabric"
  instance_class = "db.t4g.small"
  multi_az       = false
  tags           = local.tags
}

output "cluster_name"     { value = module.eks.cluster_name }
output "cluster_endpoint" { value = module.eks.cluster_endpoint }
output "rds_endpoint"     { value = module.rds.endpoint }

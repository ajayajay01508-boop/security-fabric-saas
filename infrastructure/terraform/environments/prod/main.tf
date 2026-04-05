terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = { source = "hashicorp/aws"; version = "~> 5.0" }
    kubernetes = { source = "hashicorp/kubernetes"; version = "~> 2.27" }
    helm = { source = "hashicorp/helm"; version = "~> 2.13" }
  }
  backend "s3" {
    bucket         = "security-fabric-tfstate-prod"
    key            = "prod/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "security-fabric-tflock"
  }
}

provider "aws" { region = var.aws_region }

locals {
  name = "security-fabric-prod"
  tags = {
    Project     = "security-fabric"
    Environment = "prod"
    ManagedBy   = "terraform"
  }
}

variable "aws_region"   { default = "us-east-1" }
variable "vpc_id"       { type = string }
variable "subnet_ids"   { type = list(string) }

module "eks" {
  source             = "../../modules/eks"
  cluster_name       = local.name
  region             = var.aws_region
  vpc_id             = var.vpc_id
  subnet_ids         = var.subnet_ids
  node_instance_type = "m5.2xlarge"
  desired_capacity   = 5
  min_size           = 3
  max_size           = 20
  tags               = local.tags
}

module "rds" {
  source      = "../../modules/rds"
  identifier  = "${local.name}-db"
  vpc_id      = var.vpc_id
  subnet_ids  = var.subnet_ids
  db_name     = "security_fabric"
  db_username = "fabric"
  instance_class = "db.r6g.large"
  multi_az    = true
  tags        = local.tags
}

output "cluster_name"    { value = module.eks.cluster_name }
output "cluster_endpoint"{ value = module.eks.cluster_endpoint }
output "rds_endpoint"    { value = module.rds.endpoint }

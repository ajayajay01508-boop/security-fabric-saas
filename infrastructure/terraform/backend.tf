# infrastructure/terraform/backend.tf
# Shared backend configuration for all environments.
# Each environment overrides the key in its own main.tf backend block.
#
# To bootstrap the S3 bucket + DynamoDB table for state storage:
#   aws s3 mb s3://security-fabric-tfstate-prod --region us-east-1
#   aws s3api put-bucket-versioning \
#     --bucket security-fabric-tfstate-prod \
#     --versioning-configuration Status=Enabled
#   aws dynamodb create-table \
#     --table-name security-fabric-tflock \
#     --attribute-definitions AttributeName=LockID,AttributeType=S \
#     --key-schema AttributeName=LockID,KeyType=HASH \
#     --billing-mode PAY_PER_REQUEST \
#     --region us-east-1

# This file documents the convention — actual backend blocks
# live in each environment's main.tf so they can differ by bucket.

locals {
  # Shared naming convention
  project     = "security-fabric"
  tf_state_bucket_prefix = "security-fabric-tfstate"
  tf_lock_table          = "security-fabric-tflock"
  default_region         = "us-east-1"
}

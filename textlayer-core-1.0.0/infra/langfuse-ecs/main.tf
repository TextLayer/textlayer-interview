provider "aws" {
  access_key = var.aws_access_key
  secret_key = var.aws_secret_key
  region     = var.aws_region
}

# Generate a random string to append to resource names for uniqueness
resource "random_id" "bucket_suffix" {
  byte_length = 8
}

# ECS Cluster
resource "aws_ecs_cluster" "langfuse" {
  name = "langfuse"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_cluster_capacity_providers" "langfuse" {
  cluster_name = aws_ecs_cluster.langfuse.name

  capacity_providers = ["FARGATE"]

  default_capacity_provider_strategy {
    base              = 1
    weight            = 100
    capacity_provider = "FARGATE"
  }
}

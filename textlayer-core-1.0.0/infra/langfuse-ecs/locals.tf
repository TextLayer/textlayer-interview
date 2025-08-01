locals {
  common_tags = {
    Project     = "Langfuse"
    Environment = "Production"
    Terraform   = "true"
  }

  private_subnet_ids = aws_subnet.private[*].id
  public_subnet_ids  = aws_subnet.public[*].id

  clickhouse_port     = 8123
  clickhouse_tcp_port = 9000
  postgres_port       = 5432
  redis_port          = 6379
  langfuse_web_port   = 3000

  langfuse_env_vars = {
    clickhouse = [
      {
        name  = "CLICKHOUSE_USER"
        value = var.clickhouse_username
      },
      {
        name  = "CLICKHOUSE_PASSWORD"
        value = var.clickhouse_password
      }
    ]

    web = [
      {
        name  = "DATABASE_URL"
        value = "postgresql://${var.db_username}:${var.db_password}@${aws_rds_cluster.langfuse.endpoint}:5432/${var.db_name}"
      },
      {
        name  = "REDIS_URL"
        value = "redis://${aws_elasticache_replication_group.langfuse.primary_endpoint_address}:6379"
      },
      {
        name  = "CLICKHOUSE_URL"
        value = "http://${var.clickhouse_username}:${var.clickhouse_password}@clickhouse.langfuse.local:8123/default"
      },
      {
        name  = "CLICKHOUSE_MIGRATION_URL"
        value = "clickhouse://${var.clickhouse_username}:${var.clickhouse_password}@clickhouse.langfuse.local:9000/default"
      },
      {
        name  = "CLICKHOUSE_USER"
        value = var.clickhouse_username
      },
      {
        name  = "CLICKHOUSE_PASSWORD"
        value = var.clickhouse_password
      },
      {
        name  = "CLICKHOUSE_CLUSTER_ENABLED"
        value = "false"
      },
      {
        name  = "BLOB_STORAGE_S3_ENABLED"
        value = "true"
      },
      {
        name  = "S3_BUCKET_NAME"
        value = aws_s3_bucket.langfuse.id
      },
      {
        name  = "LANGFUSE_S3_EVENT_UPLOAD_BUCKET"
        value = aws_s3_bucket.langfuse.id
      },
      {
        name  = "S3_REGION"
        value = var.aws_region
      },
      {
        name  = "NEXT_PUBLIC_LANGFUSE_CLOUD_REGION"
        value = var.next_public_langfuse_cloud_region
      },
      {
        name  = "NEXTAUTH_URL"
        value = "http://${aws_lb.langfuse.dns_name}"
      },
      {
        name  = "NEXTAUTH_SECRET"
        value = var.jwt_secret
      },
      {
        name  = "DEFAULT_ADMIN_EMAIL"
        value = var.default_admin_email
      }
    ]

    worker = [
      {
        name  = "DATABASE_URL"
        value = "postgresql://${var.db_username}:${var.db_password}@${aws_rds_cluster.langfuse.endpoint}:5432/${var.db_name}"
      },
      {
        name  = "REDIS_URL"
        value = "redis://${aws_elasticache_replication_group.langfuse.primary_endpoint_address}:6379"
      },
      {
        name  = "CLICKHOUSE_URL"
        value = "http://${var.clickhouse_username}:${var.clickhouse_password}@clickhouse.langfuse.local:8123/default"
      },
      {
        name  = "CLICKHOUSE_MIGRATION_URL"
        value = "clickhouse://${var.clickhouse_username}:${var.clickhouse_password}@clickhouse.langfuse.local:9000/default"
      },
      {
        name  = "CLICKHOUSE_USER"
        value = var.clickhouse_username
      },
      {
        name  = "CLICKHOUSE_PASSWORD"
        value = var.clickhouse_password
      },
      {
        name  = "CLICKHOUSE_CLUSTER_ENABLED"
        value = "false"
      },
      {
        name  = "BLOB_STORAGE_S3_ENABLED"
        value = "true"
      },
      {
        name  = "S3_BUCKET_NAME"
        value = aws_s3_bucket.langfuse.id
      },
      {
        name  = "LANGFUSE_S3_EVENT_UPLOAD_BUCKET"
        value = aws_s3_bucket.langfuse.id
      },
      {
        name  = "S3_REGION"
        value = var.aws_region
      }
    ]
  }
}

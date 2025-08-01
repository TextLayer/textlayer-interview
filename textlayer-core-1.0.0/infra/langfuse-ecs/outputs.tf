output "vpc_id" {
  description = "The ID of the VPC"
  value       = aws_vpc.langfuse.id
}

output "alb_dns_name" {
  description = "The DNS name of the load balancer"
  value       = aws_lb.langfuse.dns_name
}

output "postgres_endpoint" {
  description = "The endpoint of the PostgreSQL database"
  value       = aws_rds_cluster.langfuse.endpoint
  sensitive   = true
}

output "elasticache_endpoint" {
  description = "The endpoint of the ElastiCache/Valkey cluster"
  value       = aws_elasticache_replication_group.langfuse.primary_endpoint_address
  sensitive   = true
}

output "s3_bucket_name" {
  description = "The name of the S3 bucket for Langfuse blob storage"
  value       = aws_s3_bucket.langfuse.id
}

output "ecr_langfuse_web_repository_url" {
  description = "The URL of the ECR repository for Langfuse web"
  value       = aws_ecr_repository.langfuse_web.repository_url
}

output "ecr_langfuse_worker_repository_url" {
  description = "The URL of the ECR repository for Langfuse worker"
  value       = aws_ecr_repository.langfuse_worker.repository_url
}

output "ecr_clickhouse_repository_url" {
  description = "The URL of the ECR repository for Clickhouse"
  value       = aws_ecr_repository.clickhouse.repository_url
}

output "ecs_cluster_name" {
  description = "The name of the ECS cluster"
  value       = aws_ecs_cluster.langfuse.name
}

output "langfuse_web_url" {
  description = "The URL to access Langfuse web interface"
  value       = "http://${aws_lb.langfuse.dns_name}"
} 
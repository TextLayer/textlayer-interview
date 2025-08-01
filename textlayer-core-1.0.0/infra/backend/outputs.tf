# ECR Repository
output "ecr_repository_url" {
  description = "The URL of the ECR repository where you can push your Flask Docker images"
  value       = aws_ecr_repository.core_middleware.repository_url
}

output "ecr_repository_name" {
  description = "The name of the ECR repository"
  value       = aws_ecr_repository.core_middleware.name
}

# Load Balancer
output "alb_dns_name" {
  description = "The DNS name of the load balancer used to access the Flask application"
  value       = aws_lb.core_alb.dns_name
}

output "alb_zone_id" {
  description = "The zone ID of the load balancer for DNS configuration"
  value       = aws_lb.core_alb.zone_id
}

# ECS
output "ecs_cluster_name" {
  description = "The name of the ECS cluster where the application is deployed"
  value       = aws_ecs_cluster.core_cluster.name
}

output "ecs_cluster_arn" {
  description = "The ARN of the ECS cluster"
  value       = aws_ecs_cluster.core_cluster.arn
}

output "ecs_service_name" {
  description = "The name of the ECS service running the Flask application"
  value       = aws_ecs_service.core_middleware.name
}

# Security Groups
output "alb_security_group_id" {
  description = "The ID of the security group attached to the load balancer"
  value       = aws_security_group.alb_sg.id
}

output "ecs_security_group_id" {
  description = "The ID of the security group attached to the ECS tasks"
  value       = aws_security_group.ecs_sg.id
}

# Logs
output "cloudwatch_log_group_name" {
  description = "The name of the CloudWatch log group for the Flask application logs"
  value       = aws_cloudwatch_log_group.core_middleware.name
}

# Complete URL for accessing the application
output "application_url" {
  description = "The URL to access the Flask application"
  value       = "http://${aws_lb.core_alb.dns_name}"
}

# API Endpoint
output "api_endpoint" {
  description = "The API endpoint URL"
  value       = "http://${aws_lb.core_alb.dns_name}/api"
}

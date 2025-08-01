variable "aws_access_key" {
  description = "AWS sccess key for the deployment"
  type        = string
  default     = ""
}

variable "aws_secret_key" {
  description = "AWS secret key for the deployment"
  type        = string
  default     = ""
}

variable "aws_region" {
  description = "AWS region for the deployment"
  type        = string
  default     = "us-east-1"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones to use"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b"]
}

variable "s3_bucket_name" {
  description = "Name prefix for the S3 bucket for Langfuse blob storage (a random suffix will be added for uniqueness)"
  type        = string
  default     = "langfuse-blob-storage"
}

variable "db_instance_class" {
  description = "Instance class for the RDS instance"
  type        = string
  default     = "db.r5.large"
}

variable "db_name" {
  description = "Name of the Langfuse database"
  type        = string
  default     = "langfuse"
}

variable "db_username" {
  description = "Username for the Langfuse database"
  type        = string
  default     = "langfuseadmin"
}

variable "db_password" {
  description = "Password for the Langfuse database (use AWS Secrets Manager in production)"
  type        = string
  sensitive   = true
}

variable "clickhouse_username" {
  description = "Username for Clickhouse"
  type        = string
  default     = "default"
}

variable "clickhouse_password" {
  description = "Password for Clickhouse (use AWS Secrets Manager in production)"
  type        = string
  sensitive   = true
}

variable "elasticache_node_type" {
  description = "Node type for ElastiCache/Valkey cluster"
  type        = string
  default     = "cache.t3.small"
}

variable "langfuse_web_image" {
  description = "Docker image for Langfuse web application"
  type        = string
  default     = "langfuse/langfuse:latest"
}

variable "langfuse_worker_image" {
  description = "Docker image for Langfuse worker"
  type        = string
  default     = "langfuse/langfuse-worker:latest"
}

variable "clickhouse_image" {
  description = "Docker image for Clickhouse"
  type        = string
  default     = "clickhouse/clickhouse-server:latest"
}

variable "web_task_cpu" {
  description = "CPU units for the Langfuse web task"
  type        = number
  default     = 1024
}

variable "web_task_memory" {
  description = "Memory for the Langfuse web task"
  type        = number
  default     = 2048
}

variable "worker_task_cpu" {
  description = "CPU units for the Langfuse worker task"
  type        = number
  default     = 1024
}

variable "worker_task_memory" {
  description = "Memory for the Langfuse worker task"
  type        = number
  default     = 2048
}

variable "clickhouse_task_cpu" {
  description = "CPU units for the Clickhouse task"
  type        = number
  default     = 2048
}

variable "clickhouse_task_memory" {
  description = "Memory for the Clickhouse task"
  type        = number
  default     = 4096
}

// We default the value to 2 for redundancy. One goes down, the other takes over.
variable "langfuse_web_desired_count" {
  description = "Desired count of Langfuse web tasks"
  type        = number
  default     = 2
}

variable "langfuse_worker_desired_count" {
  description = "Desired count of Langfuse worker tasks"
  type        = number
  default     = 2
}

variable "clickhouse_desired_count" {
  description = "Desired count of Clickhouse tasks"
  type        = number
  default     = 1
}

variable "next_public_langfuse_cloud_region" {
  description = "Langfuse cloud region (for clientside SDK)"
  type        = string
  default     = "us"
}

variable "default_admin_email" {
  description = "Default admin email for Langfuse"
  type        = string
  default     = "admin@example.com"
}

variable "jwt_secret" {
  description = "JWT secret for Langfuse authentication"
  type        = string
  sensitive   = true
}

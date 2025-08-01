variable "aws_region" {
  description = "The region we are operating in, e.g. us-east-1"
  type        = string
}

# Environment
variable "environment" {
  description = "Environment name (e.g., dev, staging, production)"
  type        = string
  default     = "dev"
  validation {
    condition     = var.environment == "dev" || var.environment == "staging" || var.environment == "production"
    error_message = "Invalid environment. Valid values are \"dev\", \"staging\", or \"production\"."
  }
}

variable "hosted_zone" {
  description = "The base hosted zone for service DNS"
  type        = string
}

# ECS Task Configuration
variable "task_cpu" {
  description = "Amount of CPU to allocate to the ECS task (in CPU units)"
  type        = number
  default     = 1024
}

variable "task_memory" {
  description = "Amount of memory to allocate to the ECS task (in MiB)"
  type        = number
  default     = 2048
}

variable "service_desired_count" {
  description = "Number of instances of the ECS service to run"
  type        = number
  default     = 1
}

variable "middleware_image" {
  description = "Docker image for TextLayer Core middleware"
  type        = string
  default     = "textlayer/core-middleware:latest"
}

# Flask Application Settings
variable "flask_port" {
  description = "Port on which the Flask application will run"
  type        = number
  default     = 5000
}

variable "health_check_path" {
  description = "Path for ALB health check"
  type        = string
  default     = "/api/health"
}

# VPC Configuration
variable "vpc_id" {
  description = "ID of the VPC to deploy resources into"
  type        = string
}

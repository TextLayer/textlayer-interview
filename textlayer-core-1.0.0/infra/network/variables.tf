variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "domain_name" {
  description = "Domain name for Route53 zone"
  type        = string
  default     = "dev.textlayer.ai"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "azs" {
  description = "Availability zones"
  type        = list(string)
  default     = ["us-east-1a", "us-east-1b", "us-east-1c"]
}

variable "private_subnets" {
  description = "CIDR blocks for private subnets. These are internal-only subnets with no internet access. Used for resources that should be completely isolated from the internet (e.g., internal databases, caches)."
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
}

variable "public_subnets" {
  description = "CIDR blocks for public subnets. These subnets have bidirectional internet access through Internet Gateway. Used for public-facing resources that need both inbound and outbound internet access (e.g., load balancers)."
  type        = list(string)
  default     = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]
}

variable "egress_subnets" {
  description = "CIDR blocks for egress-only subnets. These subnets have outbound-only internet access through NAT Gateway. Used for resources that need to make outbound internet calls but should not accept inbound traffic (e.g., application servers, Lambda functions)."
  type        = list(string)
  default     = ["10.0.201.0/24", "10.0.202.0/24", "10.0.203.0/24"]
}

variable "aws_region" {
  description = "The region we are operating in, e.g. us-east-1"
  type        = string
}
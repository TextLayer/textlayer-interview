# Outputs
output "vpc_id" {
  description = "The ID of the VPC"
  value       = module.vpc.vpc_id
}

output "private_subnets" {
  description = "List of IDs of private subnets (internal-only resources with no internet access)"
  value       = module.vpc.intra_subnets
}

output "public_subnets" {
  description = "List of IDs of public subnets (public facing resources with bidirectional internet access)"
  value       = module.vpc.public_subnets
}

output "egress_subnets" {
  description = "List of IDs of egress subnets (resources with outbound-only internet access through NAT Gateway)"
  value       = module.vpc.private_subnets
}

output "zone_id" {
  description = "The Route53 zone ID"
  value       = aws_route53_zone.main.zone_id
}

output "certificate_arn" {
  description = "The ARN of the certificate"
  value       = aws_acm_certificate.main.arn
} 

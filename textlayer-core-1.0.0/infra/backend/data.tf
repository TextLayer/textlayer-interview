data "aws_route53_zone" "core_hosted_zone" {
  name = var.hosted_zone
}

data "aws_vpc" "core_service" {
  id = var.vpc_id
}

data "aws_subnets" "core_middleware_private" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.core_service.id]
  }
  filter {
    name   = "tag:terraform:subnet-name"
    values = ["egress"]
  }
}

data "aws_subnets" "core_middleware_public" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.core_service.id]
  }
  filter {
    name   = "tag:terraform:subnet-name"
    values = ["public"]
  }
}

data "aws_acm_certificate" "core_middleware" {
  domain   = "*.${var.hosted_zone}"
  statuses = ["ISSUED"]
}

data "aws_secretsmanager_secrets" "core_middleware_secrets" {
  filter {
    name   = "name"
    values = ["/backend"]
  }
}

data "aws_secretsmanager_secret" "core_middleware_values" {
  for_each = toset(data.aws_secretsmanager_secrets.core_middleware_secrets.names)
  name     = each.value
}

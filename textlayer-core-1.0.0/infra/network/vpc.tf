module "vpc" {
  source = "terraform-aws-modules/vpc/aws"

  name = "core-vpc"
  cidr = var.vpc_cidr

  azs             = var.azs
  private_subnets = var.egress_subnets  # These get NAT gateway (for egress-only access)
  public_subnets  = var.public_subnets  # These get Internet Gateway (for public access)
  intra_subnets   = var.private_subnets # These are truly private (no internet access)

  private_subnet_names = ["egress-subnet-1", "egress-subnet-2", "egress-subnet-3"]
  public_subnet_names  = ["public-subnet-1", "public-subnet-2", "public-subnet-3"]
  intra_subnet_names   = ["private-subnet-1", "private-subnet-2", "private-subnet-3"]

  private_subnet_tags = {
    "terraform:subnet-type" = "egress"
    "terraform:subnet-name" = "egress"
    Type                    = "egress"
    Purpose                 = "Resources that need outbound-only internet access through NAT Gateway"
    InternetAccess          = "outbound-only"
    NetworkType             = "nat-gateway"
  }

  public_subnet_tags = {
    "terraform:subnet-type" = "public"
    "terraform:subnet-name" = "public"
    Type                    = "public"
    Purpose                 = "Public facing resources with bidirectional internet access"
    InternetAccess          = "bidirectional"
    NetworkType             = "public"
  }

  intra_subnet_tags = {
    "terraform:subnet-type" = "private"
    "terraform:subnet-name" = "private"
    Type                    = "private"
    Purpose                 = "Internal resources with no internet access"
    InternetAccess          = "none"
    NetworkType             = "internal-only"
  }

  enable_nat_gateway = true
  single_nat_gateway = false
  enable_vpn_gateway = false

  private_dedicated_network_acl = true
  public_dedicated_network_acl  = true
  intra_dedicated_network_acl   = true

  enable_dns_hostnames = true
  enable_dns_support   = true

  enable_flow_log                      = true
  create_flow_log_cloudwatch_log_group = true
  create_flow_log_cloudwatch_iam_role  = true
  flow_log_max_aggregation_interval    = 60

  tags = {
    Terraform   = "true"
    Environment = var.environment
  }
}

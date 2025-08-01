locals {
  # Rename the prefix to match your app name
  app_name    = "core-middleware"
  environment = var.environment

  # Add a list of environment variables from your secrets management tool
  middleware_env_vars = []

  common_tags = {
    Application = local.app_name
    Environment = var.environment
    ManagedBy   = "Terraform"
  }

  name_prefix = "${local.app_name}-${local.environment}"
}

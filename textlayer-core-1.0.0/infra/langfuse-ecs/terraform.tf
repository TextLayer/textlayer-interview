terraform {
  // The provider (deployment) platform we use, which is AWS.
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.92.0"
    }
  }

  // This is where we store the terraform state files in order to perform operations.
  backend "s3" {
    bucket       = "tfstate-langfuse"
    key          = "state"
    region       = "us-east-1"
    encrypt      = true
    use_lockfile = true
  }
}


### Terraform init Command
terraform init -backend-config="bucket=tfstate-core-network-dev" -backend-config="key=state-core-network" -backend-config="region=us-east-1" -backend-config="encrypt=true"
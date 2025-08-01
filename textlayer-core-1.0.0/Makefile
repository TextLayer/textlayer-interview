help:
	@echo "Makefile for managing the development environment"
	@echo ""
	@echo "Usage:"
	@echo "  make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  help                Show this help message"
	@echo "  setup-terraform-state Setup AWS S3 bucket for Terraform state"

setup-terraform-state:
	aws s3api create-bucket \
		--bucket tfstate-core-dev \
		--region us-east-1 \
		--create-bucket-configuration LocationConstraint=us-east-1 \
		&& aws s3api put-public-access-block \
		--bucket tfstate-core-dev \
		--public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" \
		&& aws s3api put-bucket-versioning \
		--bucket tfstate-core-dev \
		--versioning-configuration Status=Enabled \
		&& aws s3api put-bucket-encryption \
		--bucket tfstate-core-dev \
		--server-side-encryption-configuration '{"Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]}'

	# cd infra/frontend
	# terraform init -backend-config="bucket=tfstate-core-dev" -backend-config="key=state-core" -backend-config="region=us-east-1" -backend-config="encrypt=true"

docker:
	docker build -t textlayer-core-backend -f .docker/backend/Dockerfile ./backend
	docker run --env-file ./backend/.env -p 8000:8000 textlayer-core-backend

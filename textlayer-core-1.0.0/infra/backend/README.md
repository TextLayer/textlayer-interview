# Copilot Middleware Infrastructure

This directory contains Terraform configuration for deploying the Python Flask Middleware application to AWS using ECS Fargate.

## Resources Created

* **ECR Repository**: For storing Docker images of the Flask middleware application
* **ECS Cluster**: To manage the containerized application
* **ECS Service**: Running the Flask middleware containers
* **Application Load Balancer**: For routing traffic to the API endpoints
* **Security Groups**: To control network access
* **IAM Roles**: For ECS task execution
* **CloudWatch Log Group**: For application logs

## Prerequisites

* AWS credentials with appropriate permissions
* Terraform >= 1.0.0
* An existing VPC with public and private subnets

## Configuration

TODO: Secrets management & config

## Local deployment and validation in Development ring

1. Configure AWS credentials
   ```
   # in ~\.aws\config

   [sso-session textlayer-sso]
   sso_region = us-east-1
   sso_start_url = https://d-906759e087.awsapps.com/start
      
   [profile ai-dev]
   sso_session = textlayer-sso
   sso_account_id = 050734936639
   sso_role_name = AI_Enablement_Administrator
   region = us-west-2
   ```

2. Log in to AWS and set profile
   ```
   # Powershell
   aws sso login --sso-session textlayer-sso
   $ENV:AWS_PROFILE="ai-dev"
   ```

3. Set TF_VARs
   ```
   # Powershell
   $ENV:TF_VAR_environment="dev"
   $ENV:TF_VAR_aws_region="us-west-2"
   $ENV:TF_VAR_vpc_id="vpc-0065ae053c1f3894f" # beware that this value could change in the future
   $ENV:TF_VAR_hosted_zone="dev.textlayer.ai"
   ```

4. Initialize Terraform:
   ```
   terraform init -backend-config="bucket=tfstate-copilot-dev" -backend-config="key=state-middleware" -backend-config="region=us-west-2" -backend-config="encrypt=true"
   ```

5. Plan the deployment:
   ```
   terraform plan -out=tfplan
   ```

6. Apply the changes:
   ```
   terraform apply "tfplan"
   ```

7. Validate services
   - Give the ECS task some time to initialize
   - Navigate to the `application_url` output variable in a browser

8. Destroy resources:
   ```
   terraform destroy
   ```

## Docker Image Deployment

After the infrastructure is deployed, you need to build, tag, and push your Flask application to the created ECR repository:

1. Authenticate to ECR:
   ```
   aws ecr get-login-password --region <AWS_REGION> | docker login --username AWS --password-stdin <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com
   ```

2. Build and tag your Docker image:
   ```
   docker build -t <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/copilot-middleware:latest ./middleware
   ```

3. Push the image to ECR:
   ```
   docker push <AWS_ACCOUNT_ID>.dkr.ecr.<AWS_REGION>.amazonaws.com/copilot-middleware:latest
   ```

## Flask Configuration

The Flask application is configured with the following environment variables:

- `FLASK_APP`: Set to "application.py"
- `FLASK_ENV`: Set to the environment value (e.g., "DEV", "PROD")
- `FLASK_CONFIG`: Set to the uppercase environment value (e.g., "DEV", "PROD")

You can add additional environment variables by modifying the container definitions in the ECS task definition.

## Important Notes for Flask API Applications

1. **API Endpoints**:
   - The API is accessible at `http://<ALB_DNS_NAME>/v1/<ENDPOINT>>`
   - Health check is configured at `/api/health`

2. **Security Considerations**:
   - The application runs in private subnets for enhanced security
   - Only the ALB is publicly accessible
   - Consider implementing additional security measures such as:
     - API Gateway for authentication
     - AWS WAF for protecting against common web exploits
     - HTTPS with AWS Certificate Manager

4. **Scaling**:
   - The service is configured for auto-scaling capabilities
   - Adjust the `service_desired_count` for manual scaling
   - Consider setting up auto-scaling based on CPU/memory utilization

5. **Logs and Monitoring**:
   - Application logs are sent to CloudWatch
   - Consider setting up CloudWatch alarms for monitoring

## Cleanup

To destroy the created resources:

```
terraform destroy
``` 
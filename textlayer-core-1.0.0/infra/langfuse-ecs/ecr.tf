# Create ECR Repository
resource "aws_ecr_repository" "langfuse_web" {
  name                 = "langfuse-web"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "langfuse_worker" {
  name                 = "langfuse-worker"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "clickhouse" {
  name                 = "clickhouse"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

# We push our Docker images directly to ECR upon repository creation, that way our ECS cluster
# has an image to deploy.
resource "terraform_data" "langfuse_web" {
  depends_on = [aws_ecr_repository.langfuse_web]
  provisioner "local-exec" {
    command = <<EOT
          echo "Logging in to ECR..."
          aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.langfuse_web.repository_url}
      
          echo "Pulling Docker image"
          docker pull ${var.langfuse_web_image}

          echo "Tag Docker image"
          docker tag ${var.langfuse_web_image} ${aws_ecr_repository.langfuse_web.repository_url}:latest
      
          echo "Pushing image to ECR..."
          docker push ${aws_ecr_repository.langfuse_web.repository_url}:latest
        EOT
  }
}

resource "terraform_data" "langfuse_worker" {
  depends_on = [aws_ecr_repository.langfuse_worker]
  provisioner "local-exec" {
    command = <<EOT
          echo "Logging in to ECR..."
          aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.langfuse_worker.repository_url}
      
          echo "Pulling Docker image"
          docker pull ${var.langfuse_worker_image}

          echo "Tag Docker image"
          docker tag ${var.langfuse_worker_image} ${aws_ecr_repository.langfuse_worker.repository_url}:latest
      
          echo "Pushing image to ECR..."
          docker push ${aws_ecr_repository.langfuse_worker.repository_url}:latest
        EOT
  }
}

resource "terraform_data" "clickhouse" {
  depends_on = [aws_ecr_repository.clickhouse]
  provisioner "local-exec" {
    command = <<EOT
          echo "Logging in to ECR..."
          aws ecr get-login-password --region ${var.aws_region} | docker login --username AWS --password-stdin ${aws_ecr_repository.clickhouse.repository_url}
      
          echo "Pulling Docker image"
          docker pull ${var.clickhouse_image}

          echo "Tag Docker image"
          docker tag ${var.clickhouse_image} ${aws_ecr_repository.clickhouse.repository_url}:latest
      
          echo "Pushing image to ECR..."
          docker push ${aws_ecr_repository.clickhouse.repository_url}:latest
        EOT
  }
}

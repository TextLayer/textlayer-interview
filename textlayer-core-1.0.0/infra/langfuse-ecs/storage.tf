# S3 Bucket for Blob Storage
resource "aws_s3_bucket" "langfuse" {
  bucket = "${var.s3_bucket_name}-${random_id.bucket_suffix.hex}"

  tags = {
    Name = "Langfuse Blob Storage"
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "langfuse" {
  bucket = aws_s3_bucket.langfuse.id

  rule {
    id     = "expire-old-objects"
    status = "Enabled"

    filter {
      prefix = ""
    }

    expiration {
      days = 180
    }
  }
}

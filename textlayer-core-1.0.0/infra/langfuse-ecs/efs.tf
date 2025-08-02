# EFS for Clickhouse
resource "aws_efs_file_system" "clickhouse" {
  performance_mode = "generalPurpose"
  throughput_mode  = "bursting"
  encrypted        = true

  # Add lifecycle policy to improve performance by moving infrequently accessed files to lower-cost storage
  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  tags = merge(local.common_tags, {
    Name = "langfuse-clickhouse-efs"
  })
}

# Enable automatic backups for the EFS file system
resource "aws_efs_backup_policy" "clickhouse" {
  file_system_id = aws_efs_file_system.clickhouse.id

  backup_policy {
    status = "ENABLED"
  }
}

resource "aws_efs_mount_target" "clickhouse" {
  count           = length(var.availability_zones)
  file_system_id  = aws_efs_file_system.clickhouse.id
  subnet_id       = aws_subnet.private[count.index].id
  security_groups = [aws_security_group.efs.id]
}
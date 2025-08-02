# Aurora PostgreSQL Cluster
resource "aws_db_subnet_group" "langfuse" {
  name       = "langfuse-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id

  tags = {
    Name = "Langfuse DB subnet group"
  }
}

resource "aws_rds_cluster" "langfuse" {
  cluster_identifier      = "langfuse-postgres-cluster"
  engine                  = "aurora-postgresql"
  engine_version          = "15.4"
  database_name           = var.db_name
  master_username         = var.db_username
  master_password         = var.db_password
  backup_retention_period = 7
  preferred_backup_window = "07:00-09:00"
  skip_final_snapshot     = true
  db_subnet_group_name    = aws_db_subnet_group.langfuse.name
  vpc_security_group_ids  = [aws_security_group.db.id]
  availability_zones      = var.availability_zones

  tags = {
    Name = "Langfuse PostgreSQL Cluster"
  }
}

resource "aws_rds_cluster_instance" "langfuse" {
  count                = 2
  identifier           = "langfuse-postgres-instance-${count.index}"
  cluster_identifier   = aws_rds_cluster.langfuse.id
  instance_class       = "db.r5.large"
  engine               = "aurora-postgresql"
  engine_version       = "15.4"
  db_subnet_group_name = aws_db_subnet_group.langfuse.name
}

# ElastiCache (Valkey) for Redis-compatible caching and queuing
resource "aws_elasticache_subnet_group" "langfuse" {
  name       = "langfuse-cache-subnet-group"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_elasticache_parameter_group" "langfuse" {
  name   = "langfuse-valkey-params"
  family = "valkey7"

  parameter {
    name  = "maxmemory-policy"
    value = "volatile-lru"
  }
}

resource "aws_elasticache_replication_group" "langfuse" {
  replication_group_id       = "langfuse-valkey-${random_id.bucket_suffix.hex}"
  description                = "Langfuse Valkey cluster"
  node_type                  = var.elasticache_node_type
  port                       = 6379
  parameter_group_name       = aws_elasticache_parameter_group.langfuse.name
  subnet_group_name          = aws_elasticache_subnet_group.langfuse.name
  security_group_ids         = [aws_security_group.elasticache.id]
  automatic_failover_enabled = true
  engine                     = "valkey"
  engine_version             = "7.2"
  multi_az_enabled           = true
  num_cache_clusters         = 2

  tags = {
    Name = "Langfuse Valkey Cluster"
  }
}

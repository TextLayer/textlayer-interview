# Service Discovery
resource "aws_service_discovery_private_dns_namespace" "langfuse" {
  name        = "langfuse.local"
  description = "Langfuse service discovery namespace"
  vpc         = aws_vpc.langfuse.id
}

resource "aws_service_discovery_service" "clickhouse" {
  name = "clickhouse"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.langfuse.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}

# Clickhouse ECS Task Definition and Service
resource "aws_ecs_task_definition" "clickhouse" {
  family                   = "langfuse-clickhouse"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.clickhouse_task_cpu
  memory                   = var.clickhouse_task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "clickhouse"
      image     = var.clickhouse_image
      essential = true

      portMappings = [
        {
          containerPort = 8123
          hostPort      = 8123
        },
        {
          containerPort = 9000
          hostPort      = 9000
        }
      ]

      environment = local.langfuse_env_vars.clickhouse

      mountPoints = [
        {
          sourceVolume  = "clickhouse-data"
          containerPath = "/var/lib/clickhouse"
          readOnly      = false
        }
      ]

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/langfuse-clickhouse"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
          "awslogs-create-group"  = "true"
        }
      }
    }
  ])

  volume {
    name = "clickhouse-data"

    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.clickhouse.id
      transit_encryption = "ENABLED"
      root_directory     = "/"
    }
  }

  tags = {
    Name = "Langfuse Clickhouse Task Definition"
  }
}

resource "aws_efs_access_point" "clickhouse" {
  file_system_id = aws_efs_file_system.clickhouse.id

  posix_user {
    gid = 101
    uid = 101
  }

  root_directory {
    path = "/clickhouse"
    creation_info {
      owner_gid   = 101
      owner_uid   = 101
      permissions = "755"
    }
  }
}

resource "aws_ecs_service" "clickhouse" {
  name                   = "langfuse-clickhouse"
  cluster                = aws_ecs_cluster.langfuse.id
  task_definition        = aws_ecs_task_definition.clickhouse.arn
  desired_count          = var.clickhouse_desired_count
  launch_type            = "FARGATE"
  scheduling_strategy    = "REPLICA"
  force_new_deployment   = true
  enable_execute_command = true

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.clickhouse.id, aws_security_group.efs.id]
    assign_public_ip = false
  }

  service_registries {
    registry_arn = aws_service_discovery_service.clickhouse.arn
  }

  lifecycle {
    ignore_changes = [desired_count]
  }

  depends_on = [aws_efs_mount_target.clickhouse]
}

# Langfuse Web ECS Task Definition and Service
resource "aws_ecs_task_definition" "langfuse_web" {
  family                   = "langfuse-web"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.web_task_cpu
  memory                   = var.web_task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "langfuse-web"
      image     = var.langfuse_web_image
      essential = true

      portMappings = [
        {
          containerPort = 3000
          hostPort      = 3000
        }
      ]

      environment = local.langfuse_env_vars.web

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/langfuse-web"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
          "awslogs-create-group"  = "true"
        }
      }
    }
  ])

  tags = {
    Name = "Langfuse Web Task Definition"
  }
}

resource "aws_ecs_service" "langfuse_web" {
  name                   = "langfuse-web"
  cluster                = aws_ecs_cluster.langfuse.id
  task_definition        = aws_ecs_task_definition.langfuse_web.arn
  desired_count          = var.langfuse_web_desired_count
  launch_type            = "FARGATE"
  scheduling_strategy    = "REPLICA"
  force_new_deployment   = true
  enable_execute_command = true

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.langfuse.arn
    container_name   = "langfuse-web"
    container_port   = 3000
  }

  lifecycle {
    ignore_changes = [desired_count]
  }

  depends_on = [aws_ecs_service.clickhouse]
}

# Langfuse Worker ECS Task Definition and Service
resource "aws_ecs_task_definition" "langfuse_worker" {
  family                   = "langfuse-worker"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.worker_task_cpu
  memory                   = var.worker_task_memory
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name      = "langfuse-worker"
      image     = var.langfuse_worker_image
      essential = true

      environment = local.langfuse_env_vars.worker

      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = "/ecs/langfuse-worker"
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
          "awslogs-create-group"  = "true"
        }
      }
    }
  ])

  tags = {
    Name = "Langfuse Worker Task Definition"
  }
}

resource "aws_ecs_service" "langfuse_worker" {
  name                   = "langfuse-worker"
  cluster                = aws_ecs_cluster.langfuse.id
  task_definition        = aws_ecs_task_definition.langfuse_worker.arn
  desired_count          = var.langfuse_worker_desired_count
  launch_type            = "FARGATE"
  scheduling_strategy    = "REPLICA"
  force_new_deployment   = true
  enable_execute_command = true

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  lifecycle {
    ignore_changes = [desired_count]
  }

  depends_on = [aws_ecs_service.langfuse_web]
}

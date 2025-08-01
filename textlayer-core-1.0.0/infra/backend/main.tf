provider "aws" {
  region = var.aws_region
}

# Used to generate a unique resource name by randomizing the suffix.
resource "random_id" "suffix_randomizer" {
  byte_length = 8
}

# ECR Repository
resource "aws_ecr_repository" "core_middleware" {
  name                 = local.app_name
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = local.common_tags
}

# ECS Cluster
resource "aws_ecs_cluster" "core_cluster" {
  name = "${local.name_prefix}-cluster"

  tags = local.common_tags
}

# Security Group for ALB
resource "aws_security_group" "alb_sg" {
  name        = "${local.name_prefix}-alb-sg"
  description = "Security group for ${local.name_prefix} ALB"
  vpc_id      = data.aws_vpc.core_service.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

# Security Group for ECS Tasks
resource "aws_security_group" "ecs_sg" {
  name        = "${local.name_prefix}-ecs-sg"
  description = "Security group for ${local.name_prefix} ECS tasks"
  vpc_id      = data.aws_vpc.core_service.id

  ingress {
    from_port       = var.flask_port
    to_port         = var.flask_port
    protocol        = "tcp"
    security_groups = [aws_security_group.alb_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = local.common_tags
}

resource "aws_lb" "core_alb" {
  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb_sg.id]
  subnets            = data.aws_subnets.core_middleware_public.ids

  enable_deletion_protection = false

  tags = local.common_tags
}

# ALB Target Group
resource "aws_lb_target_group" "core_tg" {
  name        = "${local.name_prefix}-tg"
  port        = var.flask_port
  protocol    = "HTTP"
  vpc_id      = data.aws_vpc.core_service.id
  target_type = "ip"

  health_check {
    path                = var.health_check_path
    healthy_threshold   = 3
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 30
    matcher             = "200-399"
  }

  tags = local.common_tags
}

# HTTPS Listener
resource "aws_lb_listener" "core_https_listener" {
  load_balancer_arn = aws_lb.core_alb.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = data.aws_acm_certificate.core_middleware.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.core_tg.arn
  }
}

# Route53 Record pointing to ALB
resource "aws_route53_record" "middleware_dns" {
  zone_id = data.aws_route53_zone.core_hosted_zone.zone_id
  name    = "core.${var.hosted_zone}"
  type    = "A"

  alias {
    name                   = aws_lb.core_alb.dns_name
    zone_id                = aws_lb.core_alb.zone_id
    evaluate_target_health = true
  }
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "core_middleware" {
  name              = "/ecs/${local.name_prefix}"
  retention_in_days = 30

  tags = local.common_tags
}

resource "aws_iam_role" "core_middleware_role" {
  name = "core-middleware-role-${random_id.suffix_randomizer.hex}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
        Sid = ""
      }
    ]
  })
}

resource "aws_iam_role_policy" "core_middleware_permissions" {
  name = "test_policy"
  role = aws_iam_role.core_middleware_role.id

  policy = <<POLICY
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
              "ecr:BatchCheckLayerAvailability",
              "ecr:GetDownloadUrlForLayer",
              "ecr:BatchGetImage",
              "ecr:GetAuthorizationToken"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
              "logs:CreateLogStream",
              "logs:PutLogEvents"
            ],
            "Resource": "*"
        },
        {
          "Effect": "Allow",
          "Action": [
            "secretsmanager:GetSecretValue"
          ],
          "Resource": "*"
        }
    ]
}
POLICY
}

resource "aws_ecs_task_definition" "core_middleware" {
  family                   = local.name_prefix
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.task_cpu
  memory                   = var.task_memory
  execution_role_arn       = aws_iam_role.core_middleware_role.arn

  container_definitions = jsonencode([
    {
      name      = local.app_name
      image     = "${aws_ecr_repository.core_middleware.repository_url}:latest"
      essential = true

      portMappings = [
        {
          containerPort = var.flask_port
          hostPort      = var.flask_port
          protocol      = "tcp"
        }
      ]
      secrets = [
        for key, param in data.aws_secretsmanager_secret.core_middleware_values :
        {
          name      = basename(key)
          valueFrom = param.arn
        }
        if param.arn != null
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          "awslogs-group"         = aws_cloudwatch_log_group.core_middleware.name
          "awslogs-region"        = var.aws_region
          "awslogs-stream-prefix" = "ecs"
        }
      }
    }
  ])

  tags = local.common_tags
}

resource "aws_ecs_service" "core_middleware" {
  name                 = "${local.name_prefix}-service"
  cluster              = aws_ecs_cluster.core_cluster.id
  task_definition      = aws_ecs_task_definition.core_middleware.arn
  desired_count        = var.service_desired_count
  launch_type          = "FARGATE"
  force_new_deployment = true

  network_configuration {
    subnets          = data.aws_subnets.core_middleware_private.ids
    security_groups  = [aws_security_group.ecs_sg.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.core_tg.arn
    container_name   = local.app_name
    container_port   = var.flask_port
  }

  depends_on = [
    aws_lb_listener.core_https_listener,
  ]

  tags = local.common_tags
}

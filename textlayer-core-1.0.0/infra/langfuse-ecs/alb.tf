# Application Load Balancer
resource "aws_lb" "langfuse" {
  name               = "langfuse-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = false

  tags = {
    Name = "Langfuse ALB"
  }
}

resource "aws_lb_target_group" "langfuse" {
  name        = "langfuse-target-group"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.langfuse.id
  target_type = "ip"

  health_check {
    enabled             = true
    interval            = 30
    path                = "/api/health"
    port                = "traffic-port"
    healthy_threshold   = 3
    unhealthy_threshold = 3
    timeout             = 5
    protocol            = "HTTP"
    matcher             = "200"
  }

  tags = {
    Name = "Langfuse Target Group"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.langfuse.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.langfuse.arn
  }
}

# Uncomment and configure this section to use HTTPS
/*
resource "aws_acm_certificate" "langfuse" {
  domain_name       = "langfuse.example.com"
  validation_method = "DNS"

  tags = {
    Name = "Langfuse Certificate"
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.langfuse.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-2016-08"
  certificate_arn   = aws_acm_certificate.langfuse.arn

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.langfuse.arn
  }
}
*/
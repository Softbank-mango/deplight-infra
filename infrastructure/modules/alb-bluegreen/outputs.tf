output "alb_arn" {
  description = "ARN of the Application Load Balancer."
  value       = aws_lb.this.arn
}

output "alb_dns_name" {
  description = "DNS name of the ALB."
  value       = aws_lb.this.dns_name
}

output "production_listener_arn" {
  description = "ARN of the production listener."
  value       = aws_lb_listener.production.arn
}

output "test_listener_arn" {
  description = "ARN of the test listener."
  value       = aws_lb_listener.test.arn
}

output "blue_target_group_arn" {
  description = "ARN of the blue target group."
  value       = aws_lb_target_group.blue.arn
}

output "blue_target_group_arn_suffix" {
  description = "ARN suffix of the blue target group."
  value       = aws_lb_target_group.blue.arn_suffix
}

output "green_target_group_arn" {
  description = "ARN of the green target group."
  value       = aws_lb_target_group.green.arn
}

output "green_target_group_arn_suffix" {
  description = "ARN suffix of the green target group."
  value       = aws_lb_target_group.green.arn_suffix
}

output "blue_target_group_name" {
  description = "Name of the blue target group."
  value       = aws_lb_target_group.blue.name
}

output "green_target_group_name" {
  description = "Name of the green target group."
  value       = aws_lb_target_group.green.name
}

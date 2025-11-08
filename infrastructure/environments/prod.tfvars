# Production environment overrides
environment_variables = {
  APP_ENV = "production"
}

container_image = "513348493870.dkr.ecr.ap-northeast-2.amazonaws.com/delightful-app:prod"
desired_count   = 3
task_cpu        = 1024
task_memory     = 2048
health_check_path = "/health"

# Dev environment overrides
environment_variables = {
  APP_ENV = "dev"
}

container_image = "513348493870.dkr.ecr.ap-northeast-2.amazonaws.com/delightful-app:dev"
desired_count   = 1
task_cpu        = 256
task_memory     = 512
health_check_path = "/"

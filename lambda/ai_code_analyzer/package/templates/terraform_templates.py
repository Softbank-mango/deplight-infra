"""
Terraform tfvars templates
Terraform 담당자가 이 파일을 수정하면 Lambda가 자동으로 반영합니다.
"""

TERRAFORM_TFVARS_TEMPLATE = """# ========================================
# AI Analyzer Generated Configuration
# Analysis ID: {analysis_id}
# Project: {primary_language} - {primary_framework}
# ========================================

# Container Configuration
image_tag = "{image_tag}"
container_port = {port}
cpu = {cpu}
memory = {memory}

# Scaling Configuration
desired_count = {desired_count}
min_capacity = {min_capacity}
max_capacity = {max_capacity}

# Auto-scaling thresholds
cpu_target_value = {cpu_target_value}
memory_target_value = {memory_target_value}

# Health Check
health_check_path = "{health_check_path}"
health_check_interval = {health_check_interval}
health_check_timeout = {health_check_timeout}
health_check_healthy_threshold = {health_check_healthy_threshold}
health_check_unhealthy_threshold = {health_check_unhealthy_threshold}

# Deployment (Blue-Green)
deployment_minimum_healthy_percent = {deployment_minimum_healthy_percent}
deployment_maximum_percent = {deployment_maximum_percent}

# Database (if needed)
database_enabled = {database_enabled}
database_engine = "{database_type}"

# ========================================
# 수정 가능한 추가 설정
# ========================================

# environment = "dev"
# log_retention_days = 7
# enable_xray_tracing = true
# enable_container_insights = true
"""


def generate_terraform_tfvars(
    analysis_id: str,
    image_tag: str,
    port: int,
    cpu: int,
    memory: int,
    scaling_config: dict,
    health_check_config: dict,
    deployment_config: dict,
    primary_language: str = "Unknown",
    primary_framework: str = "N/A",
    database_enabled: bool = False,
    database_type: str = "none"
) -> str:
    """Terraform tfvars 파일 생성"""

    return TERRAFORM_TFVARS_TEMPLATE.format(
        analysis_id=analysis_id,
        primary_language=primary_language,
        primary_framework=primary_framework,
        image_tag=image_tag,
        port=port,
        cpu=cpu,
        memory=memory,
        desired_count=scaling_config["desired_count"],
        min_capacity=scaling_config["min_capacity"],
        max_capacity=scaling_config["max_capacity"],
        cpu_target_value=scaling_config["cpu_target_value"],
        memory_target_value=scaling_config["memory_target_value"],
        health_check_path=health_check_config["path"],
        health_check_interval=health_check_config["interval"],
        health_check_timeout=health_check_config["timeout"],
        health_check_healthy_threshold=health_check_config["healthy_threshold"],
        health_check_unhealthy_threshold=health_check_config["unhealthy_threshold"],
        deployment_minimum_healthy_percent=deployment_config["minimum_healthy_percent"],
        deployment_maximum_percent=deployment_config["maximum_percent"],
        database_enabled=str(database_enabled).lower(),
        database_type=database_type
    )

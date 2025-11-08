"""
Terraform tfvars generator
Uses templates from templates/terraform_templates.py and config/resource_config.py
"""
from typing import Dict, Any
from templates.terraform_templates import generate_terraform_tfvars
from config.resource_config import (
    get_cpu, get_memory,
    SCALING_CONFIG, HEALTH_CHECK_CONFIG, DEPLOYMENT_CONFIG
)


def generate_tfvars(
    analysis_id: str,
    image_tag: str,
    project_info: Dict[str, Any]
) -> str:
    """
    프로젝트 정보를 기반으로 terraform.tfvars 생성
    config/resource_config.py 설정을 자동으로 반영합니다.
    """
    complexity = project_info.get("deployment_complexity", "moderate")
    port = project_info.get("app_port", 8000)
    primary_language = project_info.get("primary_language", "Unknown")
    primary_framework = project_info.get("primary_framework", "N/A")
    database_needed = project_info.get("database_needed", False)
    database_type = project_info.get("database_type", "none")

    # CPU/메모리는 config에서 가져옴
    cpu = get_cpu(complexity)
    memory = get_memory(complexity)

    # Terraform tfvars 생성
    tfvars = generate_terraform_tfvars(
        analysis_id=analysis_id,
        image_tag=image_tag,
        port=port,
        cpu=cpu,
        memory=memory,
        scaling_config=SCALING_CONFIG,
        health_check_config=HEALTH_CHECK_CONFIG,
        deployment_config=DEPLOYMENT_CONFIG,
        primary_language=primary_language,
        primary_framework=primary_framework,
        database_enabled=database_needed,
        database_type=database_type
    )

    return tfvars

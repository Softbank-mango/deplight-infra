"""
AppSpec generator
Uses templates from templates/appspec_templates.py
"""
from typing import Dict, Any
from templates.appspec_templates import generate_appspec


def generate_appspec_yaml(project_info: Dict[str, Any]) -> str:
    """
    프로젝트 정보를 기반으로 AppSpec YAML 생성
    CodeDeploy Blue-Green 배포에 사용됩니다.
    """
    port = project_info.get("app_port", 8000)
    return generate_appspec(port)

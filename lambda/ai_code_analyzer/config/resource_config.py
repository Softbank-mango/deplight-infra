"""
Resource configuration for deployment
Terraform 담당자가 이 파일만 수정하면 Lambda가 자동으로 반영합니다.
"""

# ===================================================================
# Terraform 리소스 크기 설정
# terraform/ecs.tf 에서 사용하는 값과 동기화해야 합니다
# ===================================================================

# CPU 할당 (단위: vCPU)
CPU_MAPPING = {
    "simple": 256,      # 0.25 vCPU - 간단한 API, static site
    "moderate": 512,    # 0.5 vCPU - 일반 웹앱, FastAPI, Express
    "complex": 1024     # 1 vCPU - 컴파일 언어, 데이터 처리
}

# 메모리 할당 (단위: MB)
MEMORY_MAPPING = {
    "simple": 512,      # 512 MB
    "moderate": 1024,   # 1 GB
    "complex": 2048     # 2 GB
}

# 기본 복잡도 (unknown일 경우)
DEFAULT_COMPLEXITY = "moderate"

# ===================================================================
# Auto-scaling 설정
# ===================================================================

SCALING_CONFIG = {
    "desired_count": 2,
    "min_capacity": 2,
    "max_capacity": 4,
    "cpu_target_value": 70,      # CPU 70% 도달 시 scale out
    "memory_target_value": 80    # Memory 80% 도달 시 scale out
}

# ===================================================================
# Health Check 설정
# ===================================================================

HEALTH_CHECK_CONFIG = {
    "path": "/health",
    "interval": 30,
    "timeout": 5,
    "healthy_threshold": 2,
    "unhealthy_threshold": 3
}

# ===================================================================
# Deployment 설정 (Blue-Green)
# ===================================================================

DEPLOYMENT_CONFIG = {
    "minimum_healthy_percent": 100,  # Blue-Green이므로 100%
    "maximum_percent": 200           # Blue-Green이므로 200%
}


def get_cpu(complexity: str) -> int:
    """복잡도에 따른 CPU 할당"""
    return CPU_MAPPING.get(complexity, CPU_MAPPING[DEFAULT_COMPLEXITY])


def get_memory(complexity: str) -> int:
    """복잡도에 따른 메모리 할당"""
    return MEMORY_MAPPING.get(complexity, MEMORY_MAPPING[DEFAULT_COMPLEXITY])

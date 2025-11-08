"""
Dockerfile generator
Uses templates from templates/dockerfile_templates.py
"""
from typing import Dict, Any
from templates.dockerfile_templates import get_dockerfile_template


def get_build_command(project_info: Dict[str, Any]) -> str:
    """언어/프레임워크에 따라 빌드 명령어 결정"""
    primary_lang = project_info.get("primary_language", "").lower()
    frameworks = [f.lower() for f in project_info.get("frameworks", [])]
    pkg_managers = project_info.get("package_managers", [])

    # Python
    if "python" in primary_lang:
        if "poetry" in pkg_managers:
            return "[\"poetry\", \"install\", \"--no-dev\"]"
        elif "pipenv" in pkg_managers:
            return "[\"pipenv\", \"install\", \"--deploy\"]"
        return "[\"pip\", \"install\", \"-r\", \"requirements.txt\"]"

    # JavaScript/TypeScript
    if "javascript" in primary_lang or "typescript" in primary_lang:
        if "yarn" in pkg_managers:
            return "[\"yarn\", \"install\", \"--production\"]"
        elif "pnpm" in pkg_managers:
            return "[\"pnpm\", \"install\", \"--prod\"]"
        return "[\"npm\", \"ci\"]"

    # Go
    if "go" in primary_lang:
        return "[\"go\", \"build\", \"-o\", \"app\", \".\"]"

    # Rust
    if "rust" in primary_lang:
        return "[\"cargo\", \"build\", \"--release\"]"

    # Java
    if "java" in primary_lang or "kotlin" in primary_lang:
        return "[\"./mvnw\", \"clean\", \"package\", \"-DskipTests\"]"

    # Ruby
    if "ruby" in primary_lang:
        return "[\"bundle\", \"install\", \"--without\", \"development\", \"test\"]"

    # PHP
    if "php" in primary_lang:
        return "[\"composer\", \"install\", \"--no-dev\", \"--optimize-autoloader\"]"

    return "[\"echo\", \"No build required\"]"


def get_start_command(project_info: Dict[str, Any]) -> str:
    """언어/프레임워크에 따라 시작 명령어 결정"""
    primary_lang = project_info.get("primary_language", "").lower()
    frameworks = [f.lower() for f in project_info.get("frameworks", [])]

    # Python
    if "python" in primary_lang:
        if any("fastapi" in f for f in frameworks):
            return "[\"uvicorn\", \"app.main:app\", \"--host\", \"0.0.0.0\", \"--port\", \"8000\"]"
        elif any("django" in f for f in frameworks):
            return "[\"gunicorn\", \"myproject.wsgi:application\", \"--bind\", \"0.0.0.0:8000\"]"
        elif any("flask" in f for f in frameworks):
            return "[\"gunicorn\", \"app:app\", \"--bind\", \"0.0.0.0:8000\"]"
        return "[\"python\", \"app.py\"]"

    # JavaScript/TypeScript
    if "javascript" in primary_lang or "typescript" in primary_lang:
        if any("next" in f for f in frameworks):
            return "[\"npm\", \"start\"]"
        elif any("express" in f for f in frameworks):
            return "[\"node\", \"server.js\"]"
        return "[\"npm\", \"start\"]"

    # Go
    if "go" in primary_lang:
        return "[\"./app\"]"

    # Rust
    if "rust" in primary_lang:
        return "[\"./target/release/app\"]"

    # Java
    if "java" in primary_lang:
        return "[\"java\", \"-jar\", \"app.jar\"]"

    return "[\"python\", \"app.py\"]"


def generate_dockerfile(project_info: Dict[str, Any]) -> str:
    """
    프로젝트 정보를 기반으로 Dockerfile 생성
    템플릿 기반이므로 수정이 쉽습니다.
    """
    primary_language = project_info.get("primary_language", "Python")
    port = project_info.get("app_port", 8000)
    start_command = get_start_command(project_info)

    # 템플릿 가져오기
    template = get_dockerfile_template(primary_language)

    # 템플릿에 값 채우기
    dockerfile = template.format(
        port=port,
        start_command=start_command
    )

    return dockerfile

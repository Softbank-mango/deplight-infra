import json
import os
import hashlib
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import boto3
import requests

# Initialize AWS clients
ssm = boto3.client("ssm")
dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")


def _fetch_github_repo_info(repository: str, commit_sha: str) -> tuple[List[str], str]:
    """
    GitHub API를 통해 repo 파일 목록과 README 가져오기
    repository: "owner/repo" 형식
    """
    import requests

    # Public API (rate limit 낮음, 하지만 demo용으로는 충분)
    api_base = "https://api.github.com"
    headers = {"Accept": "application/vnd.github.v3+json"}

    # SSM에서 GitHub token 가져오기 (선택사항)
    github_token = _get_secret_from_ssm("/delightful/github/token")
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    try:
        # 1. 파일 트리 가져오기
        tree_url = f"{api_base}/repos/{repository}/git/trees/{commit_sha}?recursive=1"
        tree_resp = requests.get(tree_url, headers=headers, timeout=10)
        tree_resp.raise_for_status()
        tree_data = tree_resp.json()

        file_list = [item["path"] for item in tree_data.get("tree", []) if item["type"] == "blob"]
        print(f"✅ Fetched {len(file_list)} files from GitHub")

        # 2. README 가져오기
        readme_url = f"{api_base}/repos/{repository}/readme"
        readme_resp = requests.get(readme_url, headers=headers, timeout=10)

        readme_content = ""
        if readme_resp.status_code == 200:
            import base64
            readme_data = readme_resp.json()
            readme_content = base64.b64decode(readme_data["content"]).decode("utf-8")
            print(f"✅ Fetched README ({len(readme_content)} chars)")

        return file_list, readme_content

    except Exception as e:
        print(f"❌ GitHub API error: {e}")
        raise


def _get_secret_from_ssm(param_name: str) -> Optional[str]:
    """Retrieve secret from SSM Parameter Store"""
    try:
        resp = ssm.get_parameter(Name=param_name, WithDecryption=True)
        return resp["Parameter"]["Value"]
    except Exception as e:
        print(f"Error retrieving SSM parameter {param_name}: {e}")
        return None


def _get_existing_deployments() -> List[Dict]:
    """Query DynamoDB for existing successful deployments to avoid conflicts"""
    try:
        # Query AI analysis table for successful deployments
        ai_analysis_table = dynamodb.Table("delightful-deploy-ai-analysis")

        response = ai_analysis_table.scan(
            FilterExpression="attribute_exists(project_info)",
            Limit=50  # Get last 50 deployments
        )

        deployments = []
        for item in response.get('Items', []):
            try:
                project_info_str = item.get('project_info', '{}')
                if isinstance(project_info_str, str):
                    project_info = json.loads(project_info_str)
                else:
                    project_info = project_info_str

                deployments.append({
                    'repository': item.get('repository', 'unknown'),
                    'port': project_info.get('app_port', 8000),
                    'language': project_info.get('primary_language', 'Unknown'),
                    'framework': project_info.get('primary_framework', 'None'),
                    'cpu': project_info.get('cpu', 256),
                    'memory': project_info.get('memory', 512)
                })
            except Exception as e:
                print(f"Error parsing deployment item: {e}")
                continue

        print(f"✅ Found {len(deployments)} existing deployments")
        return deployments

    except Exception as e:
        print(f"❌ Error querying existing deployments: {e}")
        return []


def _call_openai_api(
    base_url: str,
    api_key: str,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.3,
    response_format: Optional[Dict[str, str]] = None
) -> str:
    """
    Call OpenAI API directly using requests (no pydantic dependency)
    Returns the content of the first choice
    """
    endpoint = f"{base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature
    }

    if response_format:
        payload["response_format"] = response_format

    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            timeout=900  # 15분
        )
        response.raise_for_status()

        data = response.json()
        return data["choices"][0]["message"]["content"]

    except requests.exceptions.RequestException as e:
        print(f"Error calling OpenAI API: {e}")
        raise


def _analyze_project_with_gpt5(
    base_url: str,
    api_key: str,
    model: str,
    file_list: List[str],
    readme_content: str,
    file_samples: Optional[Dict[str, str]] = None,
    existing_deployments: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Use GPT-5 to intelligently analyze ANY project type.
    Returns comprehensive project information including language, framework, runtime, etc.
    """

    system_prompt = """You are an expert software architect and DevOps engineer with deep knowledge of:
- All programming languages (Python, JavaScript, TypeScript, Go, Rust, Java, C++, Ruby, PHP, C#, Elixir, etc.)
- All web frameworks (Django, Flask, FastAPI, Express, Next.js, React, Vue, Angular, Spring Boot, Rails, etc.)
- All build systems (Maven, Gradle, npm, yarn, pnpm, pip, poetry, cargo, go modules, etc.)
- Container technologies and deployment patterns
- Cloud infrastructure and best practices

Your task is to analyze a code repository and determine:
1. Programming language(s) used
2. Framework(s) and their versions
3. Build tools and package managers
4. Runtime requirements
5. Application type (web API, frontend, CLI, microservice, etc.)
6. Port the application typically runs on
7. Database requirements (if any)
8. External dependencies or services needed

Analyze the file structure, README, and any code samples provided. Return your analysis as a JSON object."""

    # Prepare file structure summary
    file_structure = "\n".join(file_list[:100])  # First 100 files

    # Build user prompt with all available information
    user_prompt = f"""Analyze this repository and provide detailed project information.

# File Structure
```
{file_structure}
```

# README Content
```
{readme_content[:3000] if readme_content else "No README available"}
```
"""

    if file_samples:
        user_prompt += "\n# Sample File Contents\n"
        for filename, content in file_samples.items():
            user_prompt += f"\n## {filename}\n```\n{content[:500]}\n```\n"

    # Add existing deployments context
    if existing_deployments and len(existing_deployments) > 0:
        user_prompt += f"\n\n# IMPORTANT: Existing Deployments on Mango Platform\n"
        user_prompt += "The following services are already deployed. You MUST avoid port conflicts:\n\n"

        used_ports = set()
        for dep in existing_deployments:
            port = dep.get('port', 8000)
            used_ports.add(port)
            user_prompt += f"- Repository: {dep.get('repository')}\n"
            user_prompt += f"  Language: {dep.get('language')}, Framework: {dep.get('framework')}\n"
            user_prompt += f"  Port: {port}, CPU: {dep.get('cpu')}, Memory: {dep.get('memory')}\n\n"

        user_prompt += f"\n**Used ports: {sorted(list(used_ports))}**\n"
        user_prompt += "Please select a different port that is NOT in the used ports list.\n\n"

    user_prompt += """
Return a JSON object with this structure:
{
  "languages": ["primary language", "other languages"],
  "primary_language": "main language",
  "frameworks": ["detected frameworks with versions if possible"],
  "primary_framework": "main framework or null",
  "build_tools": ["build systems"],
  "package_managers": ["package managers"],
  "runtime": "recommended runtime with version (e.g., 'Python 3.11', 'Node.js 20', 'Go 1.21')",
  "app_type": "web-api | frontend | cli | microservice | monolith | static-site | mobile-backend",
  "app_port": 8000,
  "database_needed": false,
  "database_type": "postgres | mysql | mongodb | redis | none",
  "external_services": ["list of external APIs or services"],
  "containerizable": true,
  "deployment_complexity": "simple | moderate | complex",
  "confidence": "high | medium | low",
  "notes": "Any special considerations or recommendations"
}

Only return the JSON object, nothing else."""

    try:
        content = _call_openai_api(
            base_url=base_url,
            api_key=api_key,
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        project_info = json.loads(content)

        print(f"GPT-5 Project Analysis: {json.dumps(project_info, indent=2)}")
        return project_info

    except json.JSONDecodeError as e:
        print(f"Error parsing GPT-5 JSON response: {e}")
        # Fallback to basic detection
        return _fallback_project_detection(file_list)
    except Exception as e:
        print(f"Error calling GPT-5 for project analysis: {e}")
        return _fallback_project_detection(file_list)


def _fallback_project_detection(files: List[str]) -> Dict[str, Any]:
    """Fallback project detection using simple pattern matching"""

    print("Using fallback project detection...")

    project_info = {
        "languages": [],
        "primary_language": "Unknown",
        "frameworks": [],
        "primary_framework": None,
        "build_tools": [],
        "package_managers": [],
        "runtime": "Unknown",
        "app_type": "web-api",
        "app_port": 8000,
        "database_needed": False,
        "database_type": "none",
        "external_services": [],
        "containerizable": True,
        "deployment_complexity": "moderate",
        "confidence": "low",
        "notes": "Detected using fallback pattern matching"
    }

    # Basic pattern matching
    file_patterns = {
        "package.json": {"lang": "JavaScript", "runtime": "Node.js 20", "pkg_mgr": "npm"},
        "requirements.txt": {"lang": "Python", "runtime": "Python 3.11", "pkg_mgr": "pip"},
        "go.mod": {"lang": "Go", "runtime": "Go 1.21", "pkg_mgr": "go modules"},
        "Cargo.toml": {"lang": "Rust", "runtime": "Rust 1.75", "pkg_mgr": "cargo"},
        "pom.xml": {"lang": "Java", "runtime": "Java 17", "build": "Maven"},
        "Gemfile": {"lang": "Ruby", "runtime": "Ruby 3.2", "pkg_mgr": "bundler"},
    }

    for file in files:
        for pattern, info in file_patterns.items():
            if pattern in file.lower():
                if "lang" in info:
                    project_info["primary_language"] = info["lang"]
                    project_info["languages"].append(info["lang"])
                if "runtime" in info:
                    project_info["runtime"] = info["runtime"]
                if "pkg_mgr" in info:
                    project_info["package_managers"].append(info["pkg_mgr"])

    return project_info


def _remove_heredoc_from_dockerfile(dockerfile: str) -> str:
    """
    Post-process Dockerfile to remove heredoc syntax (COPY << EOF).
    Converts heredoc patterns to RUN echo commands.
    """
    import re

    # Pattern to match COPY << heredoc blocks
    # Matches: COPY [--chown=...] << or <<' or <<- with delimiter
    heredoc_pattern = r'COPY\s+(?:--\w+=[^\s]+\s+)?<<-?[\'"]?(\w+)[\'"]?\s+([^\n]+)\n(.*?)^\1'

    def replace_heredoc(match):
        delimiter = match.group(1)
        target_path = match.group(2).strip()
        content = match.group(3)

        # Split content into lines
        lines = content.split('\n')

        # Build RUN echo commands
        echo_commands = []
        for i, line in enumerate(lines):
            # Escape special characters for shell
            escaped_line = line.replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$').replace('`', '\\`')

            if i == 0:
                # First line: overwrite file
                echo_commands.append(f'RUN echo "{escaped_line}" > {target_path}')
            else:
                # Subsequent lines: append to file
                echo_commands.append(f'    echo "{escaped_line}" >> {target_path}')

        # Add final continuation for multi-line commands
        if len(echo_commands) > 1:
            result = echo_commands[0] + ' && \\\n' + ' && \\\n'.join(echo_commands[1:])
        else:
            result = echo_commands[0] if echo_commands else ''

        return result

    # Apply regex replacement with MULTILINE and DOTALL flags
    cleaned = re.sub(heredoc_pattern, replace_heredoc, dockerfile, flags=re.MULTILINE | re.DOTALL)

    # Also check for RUN << heredoc (inline scripts)
    run_heredoc_pattern = r'RUN\s+<<-?[\'"]?(\w+)[\'"]?\n(.*?)^\1'

    def replace_run_heredoc(match):
        delimiter = match.group(1)
        script_content = match.group(2)

        # Convert to RUN with && chained commands
        lines = [l.strip() for l in script_content.split('\n') if l.strip()]
        if lines:
            return 'RUN ' + ' && \\\n    '.join(lines)
        return ''

    cleaned = re.sub(run_heredoc_pattern, replace_run_heredoc, cleaned, flags=re.MULTILINE | re.DOTALL)

    return cleaned


def _generate_deployment_specs(
    base_url: str,
    api_key: str,
    model: str,
    project_info: Dict[str, Any],
    readme_content: str,
    file_list: List[str]
) -> Dict[str, str]:
    """
    Generate deployment specifications for ANY project type using GPT-5.
    Returns Dockerfile, Terraform, AppSpec, BuildSpec, and recommendations.
    """

    system_prompt = """You are an expert DevOps engineer specialized in cloud deployments and infrastructure as code.

Your task is to generate production-ready deployment specifications for ANY type of application.

You must generate:
1. **Dockerfile** - Multi-stage build optimized for production
2. **terraform/ecs.tf** - Terraform for AWS ECS Fargate deployment
3. **appspec.yaml** - CodeDeploy Blue-Green deployment specification
4. **buildspec.yaml** - AWS CodeBuild specification for CI/CD
5. **deployment_recommendations.md** - Detailed deployment guide

Requirements for ALL specifications:
- Follow security best practices (non-root users, minimal base images, no secrets in code)
- Optimize for performance (layer caching, multi-stage builds, health checks)
- Production-ready (proper logging, graceful shutdown, resource limits)
- Cost-optimized (right-sized resources based on app complexity)

Use the project information provided to customize each specification appropriately."""

    user_prompt = f"""Generate complete deployment specifications for this project:

# Project Analysis
- **Languages**: {', '.join(project_info.get('languages', ['Unknown']))}
- **Primary Language**: {project_info.get('primary_language', 'Unknown')}
- **Frameworks**: {', '.join(project_info.get('frameworks', ['None']))}
- **Runtime**: {project_info.get('runtime', 'Unknown')}
- **App Type**: {project_info.get('app_type', 'web-api')}
- **App Port**: {project_info.get('app_port', 8000)}
- **Package Managers**: {', '.join(project_info.get('package_managers', ['Unknown']))}
- **Database**: {project_info.get('database_type', 'none')}
- **Complexity**: {project_info.get('deployment_complexity', 'moderate')}

# README Content
```
{readme_content[:2000] if readme_content else "No README available"}
```

# File Structure (sample)
```
{chr(10).join(file_list[:50])}
```

Generate COMPLETE specifications. Each file should be production-ready and fully functional.

**IMPORTANT**:
- For ECS Fargate, assume VPC, ALB, ECR repository already exist
- Use appropriate CPU/memory based on app complexity (256/512 for simple, 512/1024 for moderate, 1024/2048 for complex)
- Container port should be {project_info.get('app_port', 8000)}
- Include health check endpoint at /health
- Use Blue-Green deployment strategy with CodeDeploy
- Generate appropriate build commands for the detected language/framework

**CRITICAL - Dockerfile Requirements (MUST FOLLOW)**:
⛔ ABSOLUTELY FORBIDDEN SYNTAX:
- NEVER use: COPY << or COPY <<'...' (BuildKit heredoc) - THIS WILL FAIL!
- NEVER use: cat << EOF or cat <<'EOF' (shell heredoc)
- NEVER use: RUN <<'...' (inline scripts)
- These syntaxes are NOT supported and will cause build failures!

⛔ MULTI-STAGE BUILD WARNING:
- AVOID multi-stage builds UNLESS you properly copy Python packages
- If using multi-stage build (FROM...AS builder), you MUST copy /usr/local/lib/python*/site-packages/
- RECOMMENDED: Use single-stage build for simplicity and reliability
- Single-stage example:
  FROM python:3.11-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  COPY . .
  EXPOSE 8000
  CMD ["python", "main.py"]

✅ REQUIRED APPROACH for config files:
- MUST use RUN echo commands with proper escaping
- MUST use multiple lines with >> append for multi-line configs
- Example for nginx.conf:
  RUN echo "worker_processes 1;" > /etc/nginx/nginx.conf && \\
      echo "events { worker_connections 1024; }" >> /etc/nginx/nginx.conf && \\
      echo "http {" >> /etc/nginx/nginx.conf && \\
      echo "  server {" >> /etc/nginx/nginx.conf && \\
      echo "    listen 8506;" >> /etc/nginx/nginx.conf && \\
      echo "  }" >> /etc/nginx/nginx.conf && \\
      echo "}" >> /etc/nginx/nginx.conf
- Example for shell scripts:
  RUN echo "#!/bin/bash" > /entrypoint.sh && \\
      echo "set -e" >> /entrypoint.sh && \\
      echo "exec \\"$@\\"" >> /entrypoint.sh && \\
      chmod +x /entrypoint.sh

Return your response in this format:

---DOCKERFILE---
[Complete Dockerfile content]

---TERRAFORM---
[Complete Terraform ECS configuration]

---APPSPEC---
[Complete AppSpec YAML]

---BUILDSPEC---
[Complete BuildSpec YAML]

---RECOMMENDATIONS---
[Deployment recommendations in markdown]
"""

    try:
        # Use GPT-5 to generate all deployment specs (with heredoc prohibition)
        content = _call_openai_api(
            base_url=base_url,
            api_key=api_key,
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3
        )

        # Parse the delimited response
        specs = {
            "dockerfile": _extract_section(content, "DOCKERFILE"),
            "terraform_ecs": _extract_section(content, "TERRAFORM"),
            "appspec": _extract_section(content, "APPSPEC"),
            "buildspec": _extract_section(content, "BUILDSPEC"),
            "recommendations": _extract_section(content, "RECOMMENDATIONS")
        }

        # If parsing failed, try code block extraction as fallback
        if not specs["dockerfile"]:
            specs["dockerfile"] = _extract_code_block(content, "dockerfile") or _extract_code_block(content, "docker")
        if not specs["terraform_ecs"]:
            specs["terraform_ecs"] = _extract_code_block(content, "terraform") or _extract_code_block(content, "hcl")
        if not specs["appspec"]:
            specs["appspec"] = _extract_code_block(content, "yaml", "appspec")
        if not specs["buildspec"]:
            specs["buildspec"] = _extract_code_block(content, "yaml", "buildspec")

        # Store full response as recommendations if not extracted
        if not specs["recommendations"]:
            specs["recommendations"] = content

        # POST-PROCESSING: Remove heredoc syntax from Dockerfile
        if specs["dockerfile"]:
            original_dockerfile = specs["dockerfile"]
            cleaned_dockerfile = _remove_heredoc_from_dockerfile(original_dockerfile)

            # Check if any heredoc was found and removed
            if cleaned_dockerfile != original_dockerfile:
                print("⚠️ WARNING: Heredoc syntax detected and removed from Dockerfile")
                specs["dockerfile"] = cleaned_dockerfile
            else:
                print("✓ Dockerfile clean - no heredoc syntax detected")

        print(f"Generated specs: {list(specs.keys())}")
        return specs

    except Exception as e:
        print(f"Error generating deployment specs: {e}")
        return _generate_fallback_specs(project_info)


def _extract_section(content: str, delimiter: str) -> str:
    """Extract content between ---DELIMITER--- markers"""
    start_marker = f"---{delimiter}---"
    end_marker = "---"

    start_idx = content.find(start_marker)
    if start_idx == -1:
        return ""

    start_idx += len(start_marker)
    end_idx = content.find(end_marker, start_idx)

    if end_idx == -1:
        return content[start_idx:].strip()

    return content[start_idx:end_idx].strip()


def _extract_code_block(content: str, language: str, context: str = "") -> str:
    """Extract code from markdown code blocks"""
    marker = f"```{language}"
    start_idx = content.lower().find(marker.lower())

    # If context provided, try to find it near the code block
    if context and start_idx == -1:
        context_idx = content.lower().find(context.lower())
        if context_idx > 0:
            # Search for code block after context mention
            start_idx = content.lower().find(marker.lower(), context_idx)

    if start_idx == -1:
        return ""

    start_idx += len(marker)
    end_idx = content.find("```", start_idx)

    if end_idx == -1:
        return content[start_idx:].strip()

    return content[start_idx:end_idx].strip()


def _get_cpu_from_complexity(complexity: str) -> int:
    """프로젝트 복잡도에 따라 CPU 할당"""
    mapping = {
        "simple": 256,
        "moderate": 512,
        "complex": 1024
    }
    return mapping.get(complexity, 512)


def _get_memory_from_complexity(complexity: str) -> int:
    """프로젝트 복잡도에 따라 메모리 할당"""
    mapping = {
        "simple": 512,
        "moderate": 1024,
        "complex": 2048
    }
    return mapping.get(complexity, 1024)


def _get_build_command(project_info: Dict[str, Any]) -> str:
    """언어/프레임워크에 따라 빌드 명령어 결정"""
    primary_lang = project_info.get("primary_language", "").lower()
    frameworks = [f.lower() for f in project_info.get("frameworks", [])]
    pkg_managers = project_info.get("package_managers", [])

    # Python
    if "python" in primary_lang:
        if "poetry" in pkg_managers:
            return "poetry install --no-dev"
        elif "pipenv" in pkg_managers:
            return "pipenv install --deploy"
        return "pip install -r requirements.txt"

    # JavaScript/TypeScript
    if "javascript" in primary_lang or "typescript" in primary_lang:
        if "yarn" in pkg_managers:
            return "yarn install --production && yarn build"
        elif "pnpm" in pkg_managers:
            return "pnpm install --prod && pnpm build"
        return "npm ci && npm run build"

    # Go
    if "go" in primary_lang:
        return "go build -o app ."

    # Rust
    if "rust" in primary_lang:
        return "cargo build --release"

    # Java
    if "java" in primary_lang or "kotlin" in primary_lang:
        if "maven" in [b.lower() for b in project_info.get("build_tools", [])]:
            return "mvn clean package -DskipTests"
        return "gradle build -x test"

    # Ruby
    if "ruby" in primary_lang:
        return "bundle install --without development test"

    # PHP
    if "php" in primary_lang:
        return "composer install --no-dev --optimize-autoloader"

    return "echo 'No build required'"


def _get_start_command(project_info: Dict[str, Any]) -> str:
    """언어/프레임워크에 따라 시작 명령어 결정"""
    primary_lang = project_info.get("primary_language", "").lower()
    frameworks = [f.lower() for f in project_info.get("frameworks", [])]

    # Python
    if "python" in primary_lang:
        if any("fastapi" in f for f in frameworks):
            return "uvicorn app.main:app --host 0.0.0.0 --port 8000"
        elif any("django" in f for f in frameworks):
            return "gunicorn myproject.wsgi:application --bind 0.0.0.0:8000"
        elif any("flask" in f for f in frameworks):
            return "gunicorn app:app --bind 0.0.0.0:8000"
        return "python app.py"

    # JavaScript/TypeScript
    if "javascript" in primary_lang or "typescript" in primary_lang:
        if any("next" in f for f in frameworks):
            return "npm start"
        elif any("express" in f for f in frameworks):
            return "node server.js"
        return "npm start"

    # Go
    if "go" in primary_lang:
        return "./app"

    # Rust
    if "rust" in primary_lang:
        return "./target/release/app"

    # Java
    if "java" in primary_lang:
        return "java -jar target/app.jar"

    return "python app.py"


def _generate_terraform_tfvars(
    project_info: Dict[str, Any],
    analysis_id: str,
    image_tag: str = "latest"
) -> str:
    """Terraform에서 사용할 tfvars 파일 생성"""

    cpu = _get_cpu_from_complexity(project_info.get("deployment_complexity", "moderate"))
    memory = _get_memory_from_complexity(project_info.get("deployment_complexity", "moderate"))
    port = project_info.get("app_port", 8000)

    tfvars = f"""# Generated by AI Analyzer: {analysis_id}
# Project: {project_info.get('primary_language', 'Unknown')} - {project_info.get('primary_framework', 'N/A')}

# Container Configuration
image_tag = "{image_tag}"
container_port = {port}
cpu = {cpu}
memory = {memory}

# Scaling Configuration
desired_count = 2
min_capacity = 2
max_capacity = 4

# Auto-scaling thresholds
cpu_target_value = 70
memory_target_value = 80

# Health Check
health_check_path = "/health"
health_check_interval = 30
health_check_timeout = 5
health_check_healthy_threshold = 2
health_check_unhealthy_threshold = 3

# Deployment
deployment_minimum_healthy_percent = 100
deployment_maximum_percent = 200

# Database (if needed)
database_enabled = {str(project_info.get('database_needed', False)).lower()}
database_engine = "{project_info.get('database_type', 'none')}"
"""

    return tfvars


def _generate_fallback_specs(project_info: Dict[str, Any]) -> Dict[str, str]:
    """Generate basic fallback specs if GPT-5 generation fails"""

    runtime = project_info.get('runtime', 'python:3.11-slim')
    port = project_info.get('app_port', 8000)

    # Basic Dockerfile
    dockerfile = f"""# Multi-stage build
FROM {runtime} AS base
WORKDIR /app
COPY . .

FROM {runtime}
WORKDIR /app
COPY --from=base /app .
RUN useradd -m -u 1000 appuser
USER appuser
EXPOSE {port}
HEALTHCHECK --interval=30s CMD curl -f http://localhost:{port}/health || exit 1
CMD ["python", "app.py"]
"""

    # Basic Terraform
    terraform = f"""resource "aws_ecs_task_definition" "app" {{
  family                   = "delightful-deploy"
  requires_compatibilities = ["FARGATE"]
  network_mode            = "awsvpc"
  cpu                     = 256
  memory                  = 512

  container_definitions = jsonencode([{{
    name  = "app"
    image = "${{var.ecr_repository_url}}:latest"
    portMappings = [{{ containerPort = {port} }}]
  }}])
}}
"""

    # Basic AppSpec
    appspec = """version: 0.0
Resources:
  - TargetService:
      Type: AWS::ECS::Service
      Properties:
        TaskDefinition: <TASK_DEFINITION>
        LoadBalancerInfo:
          ContainerName: "app"
          ContainerPort: 8000
"""

    return {
        "dockerfile": dockerfile,
        "terraform_ecs": terraform,
        "appspec": appspec,
        "buildspec": "",
        "recommendations": f"Fallback specs generated for {project_info.get('primary_language', 'Unknown')} project. Please review and customize."
    }


def _store_analysis_results(
    table_name: str,
    analysis_id: str,
    repository: str,
    commit_sha: str,
    project_info: Dict,
    specs: Dict,
    recommendation: str
) -> None:
    """Store analysis results in DynamoDB"""
    table = dynamodb.Table(table_name)

    item = {
        "analysis_id": analysis_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "repository": repository,
        "commit_sha": commit_sha,
        "project_info": json.dumps(project_info),
        "specs": json.dumps(specs),
        "recommendation": recommendation,
        "ttl": int(datetime.now(timezone.utc).timestamp()) + 2592000  # 30 days
    }

    try:
        table.put_item(Item=item)
        print(f"✅ Stored analysis results: {analysis_id}")
    except Exception as e:
        print(f"❌ Error storing analysis results: {e}")


def _upload_specs_to_s3(bucket: str, analysis_id: str, specs: Dict) -> Dict[str, str]:
    """Upload generated specs to S3 and return URLs"""
    urls = {}

    for spec_name, content in specs.items():
        if not content:
            continue

        key = f"analysis/{analysis_id}/{spec_name}"

        try:
            s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=content.encode("utf-8"),
                ContentType="text/plain"
            )
            urls[spec_name] = f"s3://{bucket}/{key}"
            print(f"✅ Uploaded {spec_name} to S3")
        except Exception as e:
            print(f"❌ Error uploading {spec_name}: {e}")

    return urls


def lambda_handler(event, context):
    """
    Main Lambda handler for AI Code Analyzer

    Analyzes ANY project type and generates deployment specifications.

    Event format:
    {
        "repository": "owner/repo",
        "commit_sha": "abc123",
        "branch": "main",
        "pusher": "username",
        "timestamp": "2025-01-01T00:00:00Z",
        "file_list": ["file1.py", "file2.js", ...],  # Optional
        "readme_content": "...",  # Optional
        "file_samples": {"main.py": "content..."}  # Optional
    }
    """
    print("🌸 AI Code Analyzer invoked")
    print(f"Event: {json.dumps(event, default=str)}")

    # Use direct OpenAI API instead of letsur endpoint
    # Get OpenAI API key from SSM Parameter Store
    try:
        ssm = boto3.client('ssm', region_name='ap-northeast-2')
        response = ssm.get_parameter(Name='/delightful-deploy/openai-api-key', WithDecryption=True)
        api_key = response['Parameter']['Value']
    except Exception as e:
        print(f"❌ ERROR: Failed to get OpenAI API key from SSM: {e}")
        api_key = None

    if not api_key:
        print("❌ ERROR: OpenAI API key not configured")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "API key not configured"})
        }

    # Use direct OpenAI API endpoint
    base_url = "https://api.openai.com/v1"
    model = "gpt-4o"  # Using gpt-4o model

    print(f"✅ OpenAI API configured (base_url={base_url}, model={model})")

    # Extract environment variables
    ai_analysis_table = os.getenv("AI_ANALYSIS_TABLE", "delightful-deploy-ai-analysis")
    s3_bucket = os.getenv("S3_BUCKET", "delightful-deploy-artifacts")

    # Extract event parameters
    repository = event.get("repository", "unknown/repo")
    commit_sha = event.get("commit_sha", "unknown")
    branch = event.get("branch", "main")

    # Use analysis_id from event payload (provided by GitHub Actions workflow)
    # If not provided, fall back to generating one
    analysis_id = event.get("analysis_id")
    if not analysis_id:
        print("⚠️ No analysis_id in event, generating one...")
        analysis_id = hashlib.md5(
            f"{repository}-{commit_sha}".encode()
        ).hexdigest()[:24]

    print(f"📝 Using analysis_id: {analysis_id}")

    try:
        print(f"🔍 Analyzing repository: {repository} @ {commit_sha}")

        # Step 0: Get existing deployments to avoid conflicts
        print("📊 Querying existing deployments...")
        existing_deployments = _get_existing_deployments()

        # Get repository information from event or simulate
        file_list = event.get("file_list", [
            "README.md",
            "requirements.txt",
            "app/main.py",
            "app/__init__.py",
            "Dockerfile",
            ".gitignore"
        ])

        readme_content = event.get("readme_content", """# Demo Application

A demo application for deployment automation.

## Running locally
```
pip install -r requirements.txt
python app/main.py
```

Server runs on port 8000.
""")

        file_samples = event.get("file_samples", None)

        # Step 1: Fetch actual repository files if GitHub event
        if "github" in repository.lower():
            print("📥 Fetching repository files from GitHub...")
            try:
                # GitHub repo 형식: owner/repo
                file_list, readme_content = _fetch_github_repo_info(repository, commit_sha)
            except Exception as e:
                print(f"⚠️ Could not fetch from GitHub: {e}, using provided data")

        # Step 1.5: Analyze project using GPT-5 with existing deployment context
        print("🤖 Running intelligent project analysis...")
        project_info = _analyze_project_with_gpt5(
            base_url, api_key, model, file_list, readme_content, file_samples, existing_deployments
        )

        # Step 2: Generate deployment specs using GPT-5
        print("📦 Generating deployment specifications...")
        specs = _generate_deployment_specs(
            base_url, api_key, model, project_info, readme_content, file_list
        )

        # Step 2.5: Generate Terraform tfvars
        print("⚙️ Generating Terraform variables...")
        commit_sha_short = commit_sha[:7] if commit_sha and commit_sha != "unknown" else "latest"
        specs["terraform_tfvars"] = _generate_terraform_tfvars(
            project_info, analysis_id, commit_sha_short
        )

        # Step 3: Determine recommendation
        confidence = project_info.get("confidence", "medium")
        has_dockerfile = bool(specs.get("dockerfile"))

        if confidence == "high" and has_dockerfile:
            recommendation = "auto-apply"
            recommendation_text = f"✅ High confidence detection: {project_info.get('primary_language')} with {project_info.get('primary_framework', 'standard')} framework. Ready for deployment."
        elif confidence == "medium":
            recommendation = "review-recommended"
            recommendation_text = f"⚠️ Medium confidence detection. Please review generated specs before deployment."
        else:
            recommendation = "manual-review"
            recommendation_text = f"🔍 Low confidence or unknown project type. Manual review required."

        # Step 4: Store analysis results
        print("💾 Storing analysis results...")
        _store_analysis_results(
            ai_analysis_table, analysis_id, repository, commit_sha,
            project_info, specs, recommendation
        )

        # Step 5: Upload specs to S3
        print("☁️ Uploading specs to S3...")
        spec_urls = _upload_specs_to_s3(s3_bucket, analysis_id, specs)

        # Step 6: Prepare response for GitHub Actions
        result = {
            "analysis_id": analysis_id,
            "repository": repository,
            "commit_sha": commit_sha,
            "branch": branch,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "project_info": project_info,
            "recommendation": recommendation,
            "recommendation_text": recommendation_text,
            "spec_urls": spec_urls,
            "specs_generated": list(specs.keys()),

            # GitHub Actions가 바로 사용할 수 있는 정보
            "deployment_config": {
                "cpu": _get_cpu_from_complexity(project_info.get("deployment_complexity", "moderate")),
                "memory": _get_memory_from_complexity(project_info.get("deployment_complexity", "moderate")),
                "port": project_info.get("app_port", 8000),
                "runtime": project_info.get("runtime", "python:3.11-slim"),
                "build_command": _get_build_command(project_info),
                "start_command": _get_start_command(project_info)
            },

            # S3에서 다운로드할 파일 경로
            "download_urls": {
                "dockerfile": f"s3://{s3_bucket}/analysis/{analysis_id}/dockerfile",
                "terraform_vars": f"s3://{s3_bucket}/analysis/{analysis_id}/terraform.tfvars",
                "appspec": f"s3://{s3_bucket}/analysis/{analysis_id}/appspec.yaml"
            },

            "status": "success"
        }

        print(f"✅ Analysis complete!")
        print(f"📊 Results: {json.dumps(result, indent=2, default=str)}")

        return {
            "statusCode": 200,
            "body": json.dumps(result, default=str)
        }

    except Exception as e:
        print(f"❌ ERROR during analysis: {e}")
        import traceback
        traceback.print_exc()

        return {
            "statusCode": 500,
            "body": json.dumps({
                "analysis_id": analysis_id,
                "repository": repository,
                "commit_sha": commit_sha,
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            })
        }

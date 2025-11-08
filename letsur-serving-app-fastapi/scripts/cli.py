import ast
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import typer
from commands.envs_render import render_env_template as _render_env_template
from commands.generate_envs import (
    ENV_TEMPLATE_DOCSTRING,
    ENV_VALUES_DOCSTRING,
    extract_settings_classes_from_ast,
    find_python_files,
)
from commands.generate_openapi import get_description, get_openapi_dict, write_openapi

cli_app = typer.Typer()


@cli_app.command()
def generate(
    path: str = typer.Option(".", help="Settings 파일들을 탐색할 루트 디렉토리"),
    output_path: str = typer.Option(".", help="생성할 파일들의 디렉토리"),
    include_core: bool = typer.Option(
        False, help="env example 파일을 만들 때, core 모듈 내 환경변수도 포함할 지 여부"
    ),
    comment_if_default_value: bool = typer.Option(
        False, help="default 값이 있으면 해당 변수를 주석처리합니다."
    ),
):
    """
    프로젝트 내 BaseSettings 클래스들을 기반으로 .env.example, .env.tpl.example, .env.values.yaml.example 파일들을 정적으로 생성합니다.
    Default 값이 있는 환경변수 필드들은 해당 값을 자동으로 채웁니다. 수정을 원하시면 주석을 제거하면서 값을 수정하시면 됩니다. (BaseSettings에 작성된 기본값을 우선으로 쓰게 끔 유도.)
    """
    root_path = Path(path).resolve()
    env_example_output_path = Path(output_path).joinpath(".env.example").resolve()
    env_template_output_path = Path(output_path).joinpath(".env.tpl.example").resolve()
    env_values_output_path = (
        Path(output_path).joinpath(".env.values.yaml.example").resolve()
    )

    env_lines = {"example": [], "template": [], "values": []}
    python_files = find_python_files(root_path, include_core)

    for py_file in python_files:
        settings_classes = extract_settings_classes_from_ast(py_file)
        for class_name, fields in settings_classes:
            env_lines["example"].append(f"# --- {class_name} (from {py_file.name}) ---")
            for field, default in list(dict.fromkeys(fields)):
                if default:
                    example_line = f"{field}={default}"
                    values_line = f"  {field}: {default}"
                    template_line = f"# {default}\n{field}=${{{field}}}"
                    if comment_if_default_value:
                        example_line = "# " + example_line
                        values_line = "# " + values_line
                    env_lines["example"].append(example_line)
                    env_lines["values"].append(values_line)
                    env_lines["template"].append(template_line)
                else:
                    env_lines["example"].append(f"{field}=")
                    env_lines["template"].append(f"{field}=${{{field}}}")
                    env_lines["values"].append(f"  {field}:")
            env_lines["example"].append("")

    env_example_output_path.write_text("\n".join(env_lines["example"]))
    env_template_output_path.write_text(
        "\n".join([ENV_TEMPLATE_DOCSTRING] + env_lines["template"])
    )

    env_values_text = [ENV_VALUES_DOCSTRING]

    for stage in ["local", "dev", "stg", "prd"]:
        env_values_text.append(f"{stage}:")
        env_values_text.extend(env_lines["values"])

    env_values_output_path.write_text("\n".join(env_values_text))

    typer.echo(f"✅ .env.example 생성 완료: {env_example_output_path}")
    typer.echo(f"✅ .env.tpl.example 생성 완료: {env_template_output_path}")
    typer.echo(f"✅ .env.values.yaml.example 생성 완료: {env_values_output_path}")


@cli_app.command()
def generate_core_env(
    path: str = typer.Option(".", help="Settings 파일들을 탐색할 루트 디렉토리"),
    output_path: str = typer.Option(".", help="생성할 파일들의 디렉토리"),
    comment_if_default_value: bool = typer.Option(
        False, help="default 값이 있으면 해당 변수를 주석처리합니다."
    ),
):
    """
    프로젝트 내 BaseSettings 클래스들을 기반으로 .env.core.example 파일을 정적으로 생성합니다 (AST 기반, 안전).
    """
    root_path = Path(path).resolve()
    env_example_output_path = Path(output_path).joinpath(".env.core.example").resolve()

    env_lines = {"example": [], "template": [], "values": []}
    python_files = find_python_files(root_path, only_core=True)

    for py_file in python_files:
        settings_classes = extract_settings_classes_from_ast(py_file)
        for class_name, fields in settings_classes:
            env_lines["example"].append(f"# --- {class_name} (from {py_file.name}) ---")
            for field, default in list(dict.fromkeys(fields)):
                if default:
                    line = f"{field}={default}"
                    if comment_if_default_value:
                        line = "#  " + line
                    env_lines["example"].append(line)
                else:
                    env_lines["example"].append(f"{field}=")
            env_lines["example"].append("")

    env_lines["example"].append("# --- For Docker Compose ---")
    env_lines["example"].append('IMAGE_VERSION="v0.1.0"')

    env_example_output_path.write_text("\n".join(env_lines["example"]))
    typer.echo(f"✅ .env.core.example 생성 완료: {env_example_output_path}")


@cli_app.command()
def render_env_template():
    """
    .env.tpl 파일과 .env.values.yaml 파일을 기반으로,
    .deployment 디렉토리 내 .env.apiServer.{stage} 파일을 생성합니다.
    이미 해당 위치에 중복되는 파일들이 있을 경우, backup_{timestamp} 폴더로 이전 파일을 이동한 뒤 생성합니다.
    """
    _render_env_template()


@cli_app.command()
def generate_openapi(
    output_path: Path = typer.Option("./openapi.json", help="생성되는 openapi.json의 경로"),
    description_file_path: Optional[Path] = typer.Option(
        None,
        help="openapi.json 파일 생성 시 쓸 description 데이터, description.md 파일에 예제가 있습니다.",
    ),
):
    """
    로컬 환경에서 openapi.json 생성을 지원합니다. description path를 추가하여 description을 오버라이드할 수 있습니다.
    App Init이 필요하여 .env 파일과 .env.core를 채워주셔야 합니다. App Module Initialize 과정에서 오류가 발생하면
    환경변수, 패키지 설치, 로컬 앱 실행 여부 등을 체크하시면 됩니다.
    """
    description = None
    if description_file_path:
        description = get_description(description_file_path)

    openapi = get_openapi_dict(description=description)

    write_openapi(output_path, openapi=openapi)
    typer.echo(f"✅ openapi.json 생성 완료: {output_path}")


if __name__ == "__main__":
    cli_app()

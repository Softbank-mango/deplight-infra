"""
MCP Server for LAMP Admin CLI
"""
import os
# MCP-only: ensure no gevent monkey patching occurs
os.environ['SKIP_GEVENT_PATCH'] = 'true'
os.environ['GEVENT_SUPPORT'] = 'False'

from pathlib import Path
from functools import wraps
import logging
from typing import Optional, List
import re
from pydantic import BaseModel

# gevent 의존성을 피하기 위해 필요한 모듈만 직접 import
from lamp_admin_cli.settings import get_configure, list_configure_keys, set_env, Configure

from mcp.server.fastmcp import FastMCP


# basic logging for MCP context
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')

mcp = FastMCP("lamp-mcp")

class StandardResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict] = None


class RegisterRequest(BaseModel):
    run_id: str
    project_id: int
    profile_name: str = "default"


class CreateDummyRunRequest(BaseModel):
    # Core inputs
    project_name: Optional[str] = None
    run_name: Optional[str] = None
    profile_name: str = "default"
    # Optional stateless credentials (bypass persisted config when provided)
    lamp_environment: Optional[str] = None  # one of LAMPStage.all_values()

class UploadModelSpecRequest(BaseModel):
    run_id: str
    profile_name: str = "default"
    docker_compose_paths: Optional[List[str]] = None
    env_file_paths: Optional[List[str]] = None
    is_override: bool = False


class UploadEndpointSpecRequest(BaseModel):
    run_id: str
    profile_name: str = "default"
    build_version: Optional[str] = None
    metadata_paths: Optional[List[str]] = None
    values_paths: Optional[List[str]] = None
    env_file_paths: Optional[List[str]] = None
    openapi_paths: Optional[List[str]] = None


class ConfigureRequest(BaseModel):
    profile_name: str
    lamp_environment: str
    databricks_token: str
    github_auth_token: Optional[str] = None


class GenerateEndpointSpecRequest(BaseModel):
    """Generate endpoint spec templates under project_path/.deployment.

    Notes
    - project_path must be an absolute path; no CWD fallback.
    """
    profile_name: str = "default"
    project_path: str
    chart_version: Optional[str] = "v0.3.0"


class PopulateEndpointSpecRequest(BaseModel):
    """Populate endpoint spec files under project_path/.deployment.

    Assumes create_mcp_release has already been executed and provides
    the final image name to write into values.{stage}.yaml.

    - Copies contents of project .env into .deployment/.env.apiServer.{stage}
    - Updates values.{stage}.yaml: apiServer.deployment.image = final_image
    - If .deployment doesn't exist, it runs generate_endpoint_spec first
    """
    profile_name: str = "default"
    project_path: str
    final_image: str


class CreateMcpReleaseRequest(BaseModel):
    """Create/update a release and update docker-compose image under project_path.

    - repo: Full repository name like "owner/repo"
    - target_branch: Branch or commitish to create the tag on
    - project_path: Absolute path of the serving project root (contains docker-compose and .env.core)
    - release_name: Optional release title (defaults to new tag)
    - prerelease: Mark release as pre-release
    - tag_prefix: Tag prefix (default: mcp_v)
    - profile_name: Config profile to use
    - service_name: Compose service name containing the image (default: fastapi)
    - ecr_repo_prefix: ECR repo prefix to use before tag
    - letsur_ml_project_name: Optional override for project name if not found from files
    """
    repo: str
    target_branch: str
    project_path: str
    release_name: Optional[str] = None
    prerelease: bool = False
    tag_prefix: str = "mcp_v"
    profile_name: str = "default"
    service_name: str = "fastapi"
    ecr_repo_prefix: str = "513348493870.dkr.ecr.ap-northeast-2.amazonaws.com/delightful-deploy"
    letsur_ml_project_name: Optional[str] = None


class RunDeploymentPipelineRequest(BaseModel):
    """Run full deployment pipeline in order:

    1) create_mcp_release
    2) create_dummy_run
    3) upload_serving_model_spec
    4) upload_serving_endpoint_spec
    5) register_model

    Provide the union of parameters needed by each step. All file paths must be absolute paths.
    """
    # Common
    profile_name: str = "default"

    # Step 1: create_mcp_release
    repo: str
    target_branch: str
    project_path: str
    release_name: Optional[str] = None
    prerelease: bool = False
    tag_prefix: str = "mcp_v"
    service_name: str = "fastapi"
    ecr_repo_prefix: str = "513348493870.dkr.ecr.ap-northeast-2.amazonaws.com/delightful-deploy"
    letsur_ml_project_name: Optional[str] = None

    # Step 2: create_dummy_run
    project_name: Optional[str] = None
    run_name: Optional[str] = None
    lamp_environment: Optional[str] = None
    databricks_token: Optional[str] = None
    github_auth_token: Optional[str] = None

    # Step 3: upload_serving_model_spec
    docker_compose_paths: Optional[List[str]] = None
    env_file_paths: Optional[List[str]] = None
    is_override: bool = False

    # Step 4: upload_serving_endpoint_spec
    build_version: Optional[str] = None
    metadata_paths: Optional[List[str]] = None
    values_paths: Optional[List[str]] = None
    openapi_paths: Optional[List[str]] = None

    # Step 5: register_model
    project_id: int


def with_profile_and_mlflow(func):
    """Decorator to load profile, set env, and ensure MLflow tracking URI.

    - Resolves `request.profile_name` (defaults to "default")
    - Calls `set_env(profile)`
    - Sets MLflow tracking URI to "databricks" when mlflow is available
    - Passes computed `profile` into the wrapped function as a keyword argument

    If environment setup fails, returns a StandardResponse with failure.
    """
    @wraps(func)
    def _wrapper(request, *args, **kwargs):
        try:
            profile_name = getattr(request, "profile_name", "default") or "default"
            profile = get_configure(profile_name=profile_name)
            set_env(profile)
            try:
                from mlflow import set_tracking_uri
                set_tracking_uri("databricks")
                os.environ["MLFLOW_TRACKING_URI"] = "databricks"
            except Exception:
                # mlflow might not be available; continue silently
                pass
        except Exception as env_exc:
            return StandardResponse(
                success=False,
                message=f"Environment setup failed: {env_exc}",
                data=None,
            )
        return func(request, *args, profile=profile, **kwargs)
    return _wrapper


@mcp.tool()
@with_profile_and_mlflow
def create_dummy_run(request: CreateDummyRunRequest, profile):
    """
    MCP Tool: Create an MLflow run for deployment tracking.

    What it does
    - Loads the given profile, it loads profile from ~/.lamp/credentials. Ask user to fill credentials if empty.
    - Configures MLflow/Databricks and creates a new run in the project’s experiment.

    Inputs
    - profile_name (str, default "default")
    - project_name (str, required)
    - run_name (str, optional)

    Output (StandardResponse)
    - success (bool), message (str)
    - data: { run_id, run_name, experiment_id, project_name }

    MCP notes
    - The returned run_id is required by: upload_serving_model_spec, upload_serving_endpoint_spec, register_model.
    - Sets MLflow tracking URI to "databricks" for compatibility.
    """
    try:

        # Prepare inputs (no CWD fallback)
        if not request.project_name:
            return StandardResponse(
                success=False,
                message="project_name is required",
                data=None,
            )
        project_name = request.project_name
        run_name = request.run_name or ""

        # Import implementation after env is ready
        from lamp_admin_cli.inhouse import cli_logics as inhouse_logics

        # Create the run
        run = inhouse_logics.create_dummy_run(
            profile=profile,
            project_name=project_name,
            run_name=run_name
        )

        # Create MLBO run as well (same as CLI implementation)
        # Do not fail the whole request if MLBO is unavailable; log and continue
        try:
            from lamp_admin_cli.inhouse.mlbo.migrations import create_mlbo_run
            create_mlbo_run(profile, project_name, run_name=run_name, export_entity_id=run.info.run_id)
        except Exception as mlbo_exc:
            logging.warning("[MCP] MLBO integration failed: %s", mlbo_exc, exc_info=True)

        return StandardResponse(
            success=True,
            message=f"Successfully created dummy run {run_name or run.info.run_name} in project {project_name}",
            data={
                "run_id": run.info.run_id,
                "run_name": run.info.run_name,
                "experiment_id": run.info.experiment_id,
                "project_name": project_name
            }
        )
    except Exception as e:
        return StandardResponse(
            success=False,
            message=f"Error creating dummy run: {str(e)}",
            data=None
        )


@mcp.tool()
@with_profile_and_mlflow
def upload_serving_model_spec(request: UploadModelSpecRequest, profile):
    """
    MCP Tool: Upload serving model spec

    What it does
    - Uploads docker-compose (.yml/.yaml) and .env files to persist serving reproducibility.
    - Validates inputs, stores them in S3 under the run, and updates run tags.

    Inputs
    - run_id (str)
    - docker_compose_paths (list[str], optional) and/or env_file_paths (list[str], optional)
    - is_override (bool, default False)
    - profile_name (str, default "default")

    Output (StandardResponse)
    - success, message
    - data: { run_id, docker_compose_files, env_files }

    MCP notes
    - Typically followed by upload_serving_endpoint_spec
    - Accepts absolute paths.
    """
    try:

        # Convert string paths to Path objects and validate absoluteness
        docker_compose_paths = [Path(p) for p in request.docker_compose_paths] if request.docker_compose_paths else []
        env_file_paths = [Path(p) for p in request.env_file_paths] if request.env_file_paths else []

        for p in docker_compose_paths + env_file_paths:
            if not p.is_absolute():
                return StandardResponse(
                    success=False,
                    message=f"Path must be absolute: {p}",
                    data=None,
                )

        # Validate that both docker-compose and env files are provided
        if (not docker_compose_paths) or (not env_file_paths):
            return StandardResponse(
                success=False,
                message="All files (docker-compose, env) must be provided",
                data=None,
            )

        # Env/MLflow is set by decorator

        # Import implementation after env is ready to ensure correct initialization
        from lamp_admin_cli.inhouse import cli_logics as inhouse_logics

        # Call the actual implementation
        inhouse_logics.upload_serving_model_spec(
            profile=profile,
            run_id=request.run_id,
            docker_compose=docker_compose_paths,
            env_files=env_file_paths,
            is_override=request.is_override,
        )

        return StandardResponse(
            success=True,
            message=f"Successfully uploaded serving model spec for run {request.run_id}",
            data={
                "run_id": request.run_id,
                "docker_compose_files": len(docker_compose_paths),
                "env_files": len(env_file_paths)
            }
        )
    except Exception as e:
        return StandardResponse(
            success=False,
            message=f"Error uploading serving model spec: {str(e)}",
            data=None
        )


@mcp.tool()
@with_profile_and_mlflow
def upload_serving_endpoint_spec(request: UploadEndpointSpecRequest, profile):
    """
    MCP Tool: Upload serving endpoint spec

    What it does
    - Uploads metadata/values/env/openapi files, stores them in S3, and updates run tags.

    Inputs
    - run_id (str)
    - build_version (str, optional); if omitted, latest is inferred for the project/run
    - metadata_paths, values_paths, env_file_paths, openapi_paths (list[str], optional). Must be absolute paths.
    - profile_name (str, default "default")

    Output (StandardResponse)
    - success, message
    - data: { run_id, metadata_files, values_files, env_files, openapi_files }

    MCP notes
    - Requires upload_serving_model_spec to be completed first.
    """
    try:

        # Convert string paths to Path objects
        metadata_paths = [Path(p) for p in request.metadata_paths] if request.metadata_paths else []
        values_paths = [Path(p) for p in request.values_paths] if request.values_paths else []
        env_file_paths = [Path(p) for p in request.env_file_paths] if request.env_file_paths else []
        openapi_paths = [Path(p) for p in request.openapi_paths] if request.openapi_paths else []

        # Validate that at least one file is provided
        if not any([metadata_paths, values_paths, env_file_paths, openapi_paths]):
            return StandardResponse(
                success=False,
                message="At least one specification file must be provided",
                data=None
            )

        # Env/MLflow is set by decorator

        # Validate path lists are absolute if provided
        for paths in [request.metadata_paths, request.values_paths, request.env_file_paths, request.openapi_paths]:
            if paths:
                for p in paths:
                    if not Path(p).is_absolute():
                        return StandardResponse(
                            success=False,
                            message=f"Path must be absolute: {p}",
                            data=None,
                        )

        # Import implementation after env is ready to ensure correct initialization
        from lamp_admin_cli.inhouse import cli_logics as inhouse_logics

        # Call the actual implementation
        inhouse_logics.upload_serving_endpoint_spec(
            profile=profile,
            run_id=request.run_id,
            build_version=request.build_version or "",
            metadata_files=metadata_paths,
            values_files=values_paths,
            env_files=env_file_paths,
            openapi_files=openapi_paths
        )

        return StandardResponse(
            success=True,
            message=f"Successfully uploaded serving endpoint spec for run {request.run_id}",
            data={
                "run_id": request.run_id,
                "metadata_files": len(metadata_paths),
                "values_files": len(values_paths),
                "env_files": len(env_file_paths),
                "openapi_files": len(openapi_paths)
            }
        )
    except Exception as e:
        return StandardResponse(
            success=False,
            message=f"Error uploading serving endpoint spec: {str(e)}",
            data=None
        )


@mcp.tool()
@with_profile_and_mlflow
def register_model(request: RegisterRequest, profile):
    """
    MCP Tool: Register run to a LAMP project

    What it does
    - Registers the MLflow run as a model version under the given LAMP project.

    Inputs
    - run_id (str), project_id (int), profile_name (str, default "default")
    - 'project_id' is staix project id. Ask user to type project_id if it is missing.

    Output (StandardResponse)
    - success, message
    - data: { run_id, project_id, profile }
    """
    try:
        # Env/MLflow is set by decorator

        # Lazy import to avoid premature mlflow initialization
        from lamp_admin_cli import cli_logics as logics

        # Call the actual implementation
        logics.register(
            profile=profile,
            run_id=request.run_id,
            project_id=request.project_id
        )

        return StandardResponse(
            success=True,
            message=f"Successfully registered run_id {request.run_id} to project_id {request.project_id}",
            data={
                "run_id": request.run_id,
                "project_id": request.project_id,
                "profile": profile.name
            }
        )
    except Exception as e:
        return StandardResponse(
            success=False,
            message=f"Error registering model: {str(e)}",
            data=None
        )


@mcp.tool()
def generate_endpoint_spec(request: GenerateEndpointSpecRequest):
    """
    MCP Tool: Generate endpoint spec templates.

    What it does
    - Creates metadata/values/env template files under project_path/.deployment.

    Inputs
    - profile_name (str, default "default"), project_path (str, absolute, required), chart_version (str, optional)

    Output (StandardResponse)
    - success, message
    - data: { project_path, output_dir, chart_version, all_values, result }
    """
    try:
        # Load profile
        profile = get_configure(profile_name=request.profile_name)

        # Prepare project and output directory (require absolute path)
        project_path = Path(request.project_path)
        if not project_path.is_absolute():
            return StandardResponse(
                success=False,
                message="project_path must be an absolute path",
                data=None,
            )
        output_dir = project_path / ".deployment"
        output_dir.mkdir(exist_ok=True, parents=True)
        assert output_dir.is_dir(), "output_dir is not directory"

        # Defer import to runtime to avoid unnecessary dependencies at module import
        from lamp_admin_cli.inhouse.github import generate_endpoint_spec as _generate_endpoint_spec

        # Execute core logic
        ret = _generate_endpoint_spec(
            profile,
            output_dir=output_dir,
            chart_version=request.chart_version,
            all_values=False,
        )

        return StandardResponse(
            success=True,
            message="Successfully generated endpoint spec templates",
            data={
                "project_path": str(project_path),
                "output_dir": str(output_dir),
                "chart_version": request.chart_version,
                "all_values": False,
                "result": bool(ret),
            },
        )
    except Exception as e:
        return StandardResponse(
            success=False,
            message=f"Error generating endpoint spec: {str(e)}",
            data=None,
        )


@mcp.tool()
def populate_endpoint_spec(request: PopulateEndpointSpecRequest):
    """
    MCP Tool: Populate endpoint spec files with concrete values.

    What it does
    - Ensures project_path/.deployment exists (generates if absent).
    - Writes project .env into .deployment/.env.apiServer.{stage}.
    - Sets apiServer.deployment.image in values.{stage}.yaml to final_image.

    Inputs
    - profile_name (str, default "default")
    - project_path (str, absolute, required)
    - final_image (str): image from create_mcp_release
    - chart_version (str, optional): used only if generation is required

    Output (StandardResponse)
    - success, message
    - data: { project_path, output_dir, stage, env_target, values_path, image }
    """
    try:
        # Load profile and resolve paths (require absolute path)
        profile = get_configure(profile_name=request.profile_name)
        project_path = Path(request.project_path)
        if not project_path.is_absolute():
            return StandardResponse(
                success=False,
                message="project_path must be an absolute path",
                data=None,
            )
        output_dir = project_path / ".deployment"

        # Determine stage (fallback to 'dev')
        stage_obj = getattr(profile, "LAMP_ENVIRONMENT", None)
        stage = getattr(stage_obj, "val", None) or "dev"

        # 1) Ensure .deployment exists; generate if needed
        if not output_dir.exists():
            gen_req = GenerateEndpointSpecRequest(
                profile_name=request.profile_name,
                project_path=str(project_path),
            )
            gen_resp = generate_endpoint_spec(gen_req)
            if not gen_resp.success:
                return StandardResponse(
                    success=False,
                    message=f"Failed to generate endpoint spec: {gen_resp.message}",
                    data=gen_resp.data,
                )

        output_dir.mkdir(exist_ok=True, parents=True)

        # 2) Populate .env.apiServer.{stage} from project .env
        env_src = project_path / ".env"
        env_target = output_dir / f".env.apiServer.{stage}"
        if env_src.exists():
            env_body = env_src.read_text()
            env_target.write_text(env_body)
        else:
            # Create an empty file if source missing to keep structure consistent
            env_target.touch(exist_ok=True)

        # 3) Update values.{stage}.yaml with apiServer.deployment.image
        values_path = output_dir / f"values.{stage}.yaml"
        def _update_with_line_edit(text: str) -> str:
            lines = text.splitlines(True)

            def indent(s: str) -> int:
                return len(s) - len(s.lstrip(' '))

            api_idx = None
            api_indent = 0
            for i, l in enumerate(lines):
                if re.match(r'^\s*apiServer\s*:\s*(#.*)?$', l):
                    api_idx = i
                    api_indent = indent(l)
                    break

            if api_idx is None:
                # Append new block at end
                suffix = '' if (lines and lines[-1].endswith('\n')) else '\n'
                block = (
                    f"{suffix}apiServer:\n"
                    f"  deployment:\n"
                    f"    image: '{request.final_image}'\n"
                )
                return text + block

            # find deployment within apiServer block
            dep_idx = None
            dep_indent = 0
            i = api_idx + 1
            while i < len(lines) and (indent(lines[i]) > api_indent or lines[i].strip() == ''):
                if re.match(r'^\s*deployment\s*:\s*(#.*)?$', lines[i]):
                    dep_idx = i
                    dep_indent = indent(lines[i])
                    break
                i += 1

            if dep_idx is None:
                # insert deployment block right after apiServer
                insert_at = api_idx + 1
                newline = '' if lines[api_idx].endswith('\n') else '\n'
                insert_text = (
                    f"{newline}{' ' * (api_indent + 2)}deployment:\n"
                    f"{' ' * (api_indent + 4)}image: '{request.final_image}'\n"
                )
                lines.insert(insert_at, insert_text)
                return ''.join(lines)

            # Search for image under deployment
            j = dep_idx + 1
            image_line_idx = None
            while j < len(lines) and (indent(lines[j]) > dep_indent or lines[j].strip() == ''):
                if re.match(r'^\s*image\s*:', lines[j]):
                    image_line_idx = j
                    break
                j += 1

            if image_line_idx is not None:
                m = re.match(r'^(\s*image\s*:\s*)([^#\n]*?)(\s*(#.*)?)\r?\n?$', lines[image_line_idx])
                if m:
                    prefix, _old, suffix = m.group(1), m.group(2), m.group(3) or ''
                    ending = '\n' if lines[image_line_idx].endswith('\n') else ''
                    lines[image_line_idx] = f"{prefix}'{request.final_image}'{suffix}{ending}"
                    return ''.join(lines)

            # Not found -> insert image line after deployment header
            insert_at = dep_idx + 1
            indent_str = ' ' * (dep_indent + 2)
            ending = '' if lines[dep_idx].endswith('\n') else '\n'
            lines.insert(insert_at, f"{ending}{indent_str}image: '{request.final_image}'\n")
            return ''.join(lines)

        orig_text = values_path.read_text() if values_path.exists() else ''
        # Line-based edit to preserve comments as much as possible
        new_text = _update_with_line_edit(orig_text)
        values_path.write_text(new_text)

        return StandardResponse(
            success=True,
            message="Successfully populated endpoint spec files",
            data={
                "project_path": str(project_path),
                "output_dir": str(output_dir),
                "stage": stage,
                "env_target": str(env_target),
                "values_path": str(values_path),
                "image": request.final_image,
            },
        )
    except Exception as e:
        return StandardResponse(
            success=False,
            message=f"Error populating endpoint spec: {str(e)}",
            data=None,
        )


@mcp.tool()
def create_mcp_release(request: CreateMcpReleaseRequest):
    """
    MCP Tool: Create release and update docker-compose image tag.

    What it does
    - Computes the next tag matching {tag_prefix}{n} and creates/updates a GitHub release.
    - Optionally updates the docker-compose service image to {ecr_repo_prefix}:{project}-{tag}.

    Inputs
    - repo (str), target_branch (str), project_path (str, absolute)
    - release_name (str, optional), prerelease (bool, optional), tag_prefix (str, default "mcp_v")
    - service_name (str, default "fastapi"), ecr_repo_prefix (str), letsur_ml_project_name (str, optional), profile_name (str, default "default")

    Output (StandardResponse)
    - success, message
    - data: { repo, tag, name, target_branch, prerelease, release_url, release_id, project_path, docker_compose_path, compose_updated, final_image, project_name, service_name }
    """
    try:
        profile = get_configure(profile_name=request.profile_name)

        # Lazy import to avoid module side-effects
        from lamp_admin_cli.inhouse.github import (
            list_repo_tag_names as _list_tags,
            create_git_release as _create_release,
        )

        tags = _list_tags(profile=profile, repo=request.repo)

        # Determine next tag in the form {prefix}{number}
        import re
        pattern = re.compile(rf"^{re.escape(request.tag_prefix)}(\d+)$")
        numbers = []
        for t in tags:
            m = pattern.match(t)
            if m:
                try:
                    numbers.append(int(m.group(1)))
                except ValueError:
                    continue

        next_num = (max(numbers) + 1) if numbers else 1
        new_tag = f"{request.tag_prefix}{next_num}"

        name = request.release_name or new_tag
        release = _create_release(
            profile=profile,
            repo=request.repo,
            tag=new_tag,
            name=name,
            target_commitish=request.target_branch,
            prerelease=request.prerelease,
        )

        # Update docker-compose image via helper to keep logic isolated
        try:
            from lamp_admin_cli.inhouse.model_spec import update_docker_compose_image
            # project_path must be absolute and present
            base_dir = Path(request.project_path)
            if not base_dir.is_absolute():
                return StandardResponse(
                    success=False,
                    message="project_path must be an absolute path",
                    data=None,
                )
            result = update_docker_compose_image(
                docker_compose_path=None,
                base_dir=base_dir,
                env_core_path=None,
                service_name=request.service_name,
                ecr_repo_prefix=request.ecr_repo_prefix,
                tag=new_tag,
                project_name_override=request.letsur_ml_project_name,
            )
        except Exception as exc:
            logging.warning("[MCP] docker-compose update failed: %s", exc, exc_info=True)
            result = {
                "compose_updated": False,
                "final_image": None,
                "docker_compose_path": None,
                "project_name": request.letsur_ml_project_name,
                "service_name": request.service_name,
            }

        return StandardResponse(
            success=True,
            message=(
                f"Created release '{name}' with tag '{new_tag}'" + (" and updated docker-compose" if result.get("compose_updated") else "")
            ),
            data={
                "repo": request.repo,
                "tag": new_tag,
                "name": name,
                "target_branch": request.target_branch,
                "prerelease": request.prerelease,
                "release_url": getattr(release, "html_url", None),
                "release_id": getattr(release, "id", None),
                "project_path": request.project_path,
                "docker_compose_path": result.get("docker_compose_path"),
                "compose_updated": result.get("compose_updated"),
                "final_image": result.get("final_image"),
                "project_name": result.get("project_name"),
                "service_name": result.get("service_name"),
            },
        )
    except Exception as e:
        return StandardResponse(
            success=False,
            message=f"Error creating MCP release: {str(e)}",
            data=None,
        )


@mcp.tool()
def run_deployment_pipeline(request: RunDeploymentPipelineRequest):
    """
    MCP Tool: Run full deployment pipeline.

    Order
    - create_mcp_release → create_dummy_run → upload_serving_model_spec → upload_serving_endpoint_spec → register_model

    What it does
    - Sequentially runs the tools above and stops on first failure.
    - Aggregates each step's StandardResponse under data.

    I/O
    - Input: RunDeploymentPipelineRequest (union of parameters required by all steps)
    - Output: StandardResponse { success, message, data (per-step results) }
    """
    results: dict = {}

    # Step 1: Release
    release_req = CreateMcpReleaseRequest(
        repo=request.repo,
        target_branch=request.target_branch,
        project_path=request.project_path,
        release_name=request.release_name,
        prerelease=request.prerelease,
        tag_prefix=request.tag_prefix,
        profile_name=request.profile_name,
        service_name=request.service_name,
        ecr_repo_prefix=request.ecr_repo_prefix,
        letsur_ml_project_name=request.letsur_ml_project_name,
    )
    release_resp = create_mcp_release(release_req)
    results["create_mcp_release"] = release_resp.dict()
    if not release_resp.success:
        return StandardResponse(success=False, message="create_mcp_release failed", data=results)

    # Populate endpoint spec between release and dummy run
    try:
        release_data = release_resp.data or {}
        final_image = release_data.get("final_image")
        tag = release_data.get("tag")
        project_path = request.project_path
        if not Path(project_path).is_absolute():
            return StandardResponse(success=False, message="project_path must be an absolute path", data=results)
        if not final_image:
            # Fallback: construct final_image from inputs
            # Prefer project_name from release, else letsur_ml_project_name, else folder name
            pn = release_data.get("project_name") or request.letsur_ml_project_name or Path(project_path).name
            if pn and tag:
                final_image = f"{request.ecr_repo_prefix}:{pn}-{tag}"
        if final_image:
            pes_req = PopulateEndpointSpecRequest(
                profile_name=request.profile_name,
                project_path=project_path,
                final_image=final_image,
            )
            pes_resp = populate_endpoint_spec(pes_req)
            results["populate_endpoint_spec"] = pes_resp.dict()
            if not pes_resp.success:
                return StandardResponse(success=False, message="populate_endpoint_spec failed", data=results)
        else:
            # If we cannot determine final_image, skip with a note
            results["populate_endpoint_spec"] = {
                "success": False,
                "message": "Skipped: could not determine final_image",
                "data": {"project_path": project_path},
            }
            return StandardResponse(success=False, message="populate_endpoint_spec skipped: final_image missing", data=results)
    except Exception as _e:
        return StandardResponse(success=False, message=f"populate_endpoint_spec error: {_e}", data=results)

    # Step 2: Dummy run
    dummy_req = CreateDummyRunRequest(
        project_name=request.project_name or request.letsur_ml_project_name,
        run_name=request.run_name,
        profile_name=request.profile_name,
        lamp_environment=request.lamp_environment,
    )
    dummy_resp = create_dummy_run(dummy_req)
    results["create_dummy_run"] = dummy_resp.dict()
    if not dummy_resp.success:
        return StandardResponse(success=False, message="create_dummy_run failed", data=results)
    run_id = (dummy_resp.data or {}).get("run_id")
    if not run_id:
        return StandardResponse(success=False, message="create_dummy_run did not return run_id", data=results)

    # Step 3: Upload model spec
    model_spec_req = UploadModelSpecRequest(
        run_id=run_id,
        profile_name=request.profile_name,
        docker_compose_paths=request.docker_compose_paths or [],
        env_file_paths=request.env_file_paths or [],
        is_override=request.is_override,
    )
    model_spec_resp = upload_serving_model_spec(model_spec_req)
    results["upload_serving_model_spec"] = model_spec_resp.dict()
    if not model_spec_resp.success:
        return StandardResponse(success=False, message="upload_serving_model_spec failed", data=results)

    # Step 4: Upload endpoint spec
    endpoint_spec_req = UploadEndpointSpecRequest(
        run_id=run_id,
        profile_name=request.profile_name,
        build_version=request.build_version,
        metadata_paths=request.metadata_paths or [],
        values_paths=request.values_paths or [],
        env_file_paths=request.env_file_paths or [],
        openapi_paths=request.openapi_paths or [],
    )
    endpoint_spec_resp = upload_serving_endpoint_spec(endpoint_spec_req)
    results["upload_serving_endpoint_spec"] = endpoint_spec_resp.dict()
    if not endpoint_spec_resp.success:
        return StandardResponse(success=False, message="upload_serving_endpoint_spec failed", data=results)

    # Step 5: Register model
    register_req = RegisterRequest(
        run_id=run_id,
        project_id=request.project_id,
        profile_name=request.profile_name,
    )
    register_resp = register_model(register_req)
    results["register_model"] = register_resp.dict()
    if not register_resp.success:
        return StandardResponse(success=False, message="register_model failed", data=results)

    return StandardResponse(
        success=True,
        message="Deployment pipeline completed successfully",
        data=results,
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")

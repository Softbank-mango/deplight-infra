import logging
from pathlib import Path
from typing import Optional, Dict, Any

import yaml


DEFAULT_PROJECT_NAME = "letsur-common-app"
DEFAULT_SERVICE_NAME = "fastapi"
DEFAULT_ECR_REPO_PREFIX = (
    "513348493870.dkr.ecr.ap-northeast-2.amazonaws.com/delightful-deploy"
)


def _read_env_core_value(env_core_path: Path, key: str) -> Optional[str]:
    """Read KEY=VALUE or 'export KEY=VALUE' style entries from .env.core.

    - Ignores empty lines and full-line comments starting with '#'.
    - Supports values wrapped in single or double quotes.
    - Strips inline trailing comments for unquoted values (after '#').
    """
    if not env_core_path.exists():
        return None
    try:
        with open(env_core_path, "r") as f:
            for raw in f:
                s = raw.strip()
                if not s or s.startswith("#"):
                    continue
                if s.startswith("export "):
                    s = s[len("export "):].strip()
                if "=" not in s:
                    continue
                k, v = s.split("=", 1)
                if k.strip() != key:
                    continue
                val = v.strip()
                # Remove inline comments for unquoted values
                if not (val.startswith('"') or val.startswith("'")):
                    hash_pos = val.find('#')
                    if hash_pos != -1:
                        val = val[:hash_pos].rstrip()
                # Strip surrounding quotes if present
                if (val.startswith('"') and val.endswith('"')) or (
                    val.startswith("'") and val.endswith("'")
                ):
                    val = val[1:-1]
                return val
    except Exception as exc:
        logging.warning("[model_spec] Failed to parse %s: %s", env_core_path, exc)
    return None


def resolve_project_name(
    override: Optional[str] = None,
    env_core_path: Optional[Path] = None,
    default: str = DEFAULT_PROJECT_NAME,
) -> str:
    if override and override.strip():
        return override.strip()
    if env_core_path:
        v = _read_env_core_value(env_core_path, "LETSUR_ML_PROJECT_NAME")
        if v:
            return v
    return default


def _resolve_compose_path(candidate: Path, base_dir: Optional[Path] = None) -> Path:
    """Resolve docker-compose path with smart fallbacks and base_dir support.

    Resolution order:
    1) Absolute candidate
    2) base_dir/candidate (if base_dir provided)
    3) CWD/candidate
    For each, fallback between .yml and .yaml, and try docker-compose.yaml.
    Returns the first existing path or the last checked candidate if none found.
    """
    def try_variants(base: Path) -> Optional[Path]:
        if base.exists():
            return base
        # fallback between .yml and .yaml
        if base.suffix in {".yml", ".yaml"}:
            alt = base.with_suffix(".yaml" if base.suffix == ".yml" else ".yml")
            if alt.exists():
                return alt
        # final common name in same dir
        common = base.with_name("docker-compose.yaml")
        if common.exists():
            return common
        return None

    # 1) Absolute candidate
    if candidate.is_absolute():
        return try_variants(candidate) or candidate

    # 2) base_dir/candidate
    if base_dir is not None:
        p = (base_dir / candidate)
        found = try_variants(p)
        if found is not None:
            return found

    # 3) CWD/candidate
    p = Path.cwd() / candidate
    return try_variants(p) or p


def _resolve_optional_path(p: Optional[Path], base_dir: Optional[Path], default: Optional[Path]) -> Optional[Path]:
    if p is None:
        p = default
    if p is None:
        return None
    if p.is_absolute() or base_dir is None:
        return p
    return base_dir / p


def update_docker_compose_image(
    *,
    docker_compose_path: Optional[Path] = None,
    base_dir: Optional[Path] = None,
    env_core_path: Optional[Path] = None,
    service_name: str = DEFAULT_SERVICE_NAME,
    ecr_repo_prefix: str = DEFAULT_ECR_REPO_PREFIX,
    tag: str,
    project_name_override: Optional[str] = None,
) -> Dict[str, Any]:
    """Update docker-compose service image to a concrete ECR image 'prefix:{project}-{tag}'.

    Returns dict with:
      - compose_updated: bool
      - final_image: Optional[str]
      - docker_compose_path: str (resolved)
      - project_name: str
      - service_name: str
    """
    compose_path = _resolve_compose_path(
        Path(docker_compose_path) if docker_compose_path else Path("docker-compose.yml"),
        base_dir=base_dir,
    )

    # Resolve metadata files relative to base_dir if provided
    env_core_path = _resolve_optional_path(
        Path(env_core_path) if env_core_path else None,
        base_dir,
        default=(Path(".env.core") if base_dir is not None else None),
    )

    project_name = resolve_project_name(
        override=project_name_override,
        env_core_path=env_core_path,
        default=DEFAULT_PROJECT_NAME,
    )

    result: Dict[str, Any] = {
        "compose_updated": False,
        "final_image": None,
        "docker_compose_path": str(compose_path),
        "project_name": project_name,
        "service_name": service_name,
    }

    if not compose_path.exists():
        logging.info("[model_spec] docker-compose not found at %s; skipping update", compose_path)
        return result

    try:
        with open(compose_path, "r") as f:
            compose = yaml.safe_load(f) or {}

        services = compose.get("services") or {}
        service = services.get(service_name) or {}
        final_image = f"{ecr_repo_prefix}:{project_name}-{tag}"
        service["image"] = final_image
        services[service_name] = service
        compose["services"] = services

        with open(compose_path, "w") as f:
            yaml.safe_dump(compose, f, sort_keys=False)

        result["compose_updated"] = True
        result["final_image"] = final_image
        return result
    except Exception as exc:
        logging.warning("[model_spec] Failed to update docker-compose: %s", exc, exc_info=True)
        return result

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


ENV_VALUES_DOCSTRING = """\
# .env.tpl으로 부터 .env, .env.apiServer.dev, ... 등을 만드는데 쓰이는 values 파일의 example
# 실제로는 .env.values.yaml 파일을 써서 랜더링하며, .env.values.yaml는 gitignore에 등록되어 있음.

# local은 .env 파일을 만드는데 쓰임. 주석처리 시 .env 파일을 오버라이드하지 않음.

# local:
#   CELERY_WORKER_NUM: 1

# 나머지는 .deployment 폴더에 serving endpoint spec upload를 위한 .env 파일로 랜더링 된다.
"""

ENV_TEMPLATE_DOCSTRING = """\
### SECRET한 값은 여기에 넣지 마시고, .env.values.yaml을 사용하세요.
"""


def serialize_env_value(value: Any) -> str:
    if isinstance(value, bool):
        return '"true"' if value else '"false"'
    if isinstance(value, (int, float)):
        return f'"{str(value)}"'
    if value is None:
        return ""
    value_str = str(value)
    if value_str.startswith('"') and value_str.endswith('"'):
        return value_str
    return f'"{value_str}"'


def extract_default_from_field_call(call_node: ast.Call) -> Optional[Any]:
    for kw in call_node.keywords:
        if kw.arg == "default":
            try:
                return ast.literal_eval(kw.value)
            except Exception:
                return None
    # positional 방식: Field("value")
    if call_node.args:
        try:
            return ast.literal_eval(call_node.args[0])
        except Exception:
            return None
    return None


def find_python_files(root: Path, include_core: bool = False, only_core: bool = False):
    def is_allow(f: Path) -> bool:
        # 기본 필터 조건
        is_not_venv = "venv" not in f.parts
        is_not_dunder = not f.name.startswith("__")
        is_in_src = "src" in f.parts
        is_in_core = "_core" in f.parts
        if only_core:
            return is_not_venv and is_not_dunder and is_in_core
        if include_core:
            return is_not_venv and is_not_dunder and is_in_src
        else:
            return is_not_venv and is_not_dunder and is_in_src and not is_in_core

    return [f for f in root.rglob("*.py") if is_allow(f)]


def extract_settings_classes_from_ast(
    py_file: Path,
) -> List[Tuple[str, List[Tuple[str, Optional[str]]]]]:
    """
    해당 .py 파일에서 BaseSettings를 상속한 클래스와 그 클래스의 필드, 기본값을 추출
    반환: [(class_name, [(field_name, default_value), ...])]
    """
    with open(py_file, "r", encoding="utf-8") as f:
        source = f.read()

    try:
        tree = ast.parse(source, filename=str(py_file))
    except SyntaxError:
        return []

    settings = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            bases = [b.id for b in node.bases if isinstance(b, ast.Name)]
            if "BaseSettings" in bases:
                fields = []
                for stmt in node.body:
                    name = None
                    default = None

                    if isinstance(stmt, ast.AnnAssign) and isinstance(
                        stmt.target, ast.Name
                    ):
                        name = stmt.target.id
                        if stmt.value:
                            if (
                                isinstance(stmt.value, ast.Call)
                                and getattr(stmt.value.func, "id", "") == "Field"
                            ):
                                default = extract_default_from_field_call(stmt.value)
                            else:
                                try:
                                    default = ast.literal_eval(stmt.value)
                                except Exception:
                                    default = None

                    elif isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            if isinstance(target, ast.Name):
                                name = target.id
                                try:
                                    default = ast.literal_eval(stmt.value)
                                except Exception:
                                    default = None

                    default = serialize_env_value(default)
                    if name:
                        fields.append((name, default))
                fields = list(dict.fromkeys(fields))  # remove dup, keep order
                settings.append((node.name, fields))

    return settings

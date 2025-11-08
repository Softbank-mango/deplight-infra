import shutil
from datetime import datetime
from pathlib import Path
from string import Template

import yaml

SERVERS = ["apiServer"]
STAGES = ["dev", "stg", "prd"]
OUTPUT_DIR = Path(".deployment")


def render_env_template():
    template_path = Path(".env.tpl")
    value_path = Path(".env.values.yaml")
    with open(template_path, "r") as f:
        template = Template(f.read())

    with open(value_path, "r") as f:
        values = yaml.safe_load(f)

    server = SERVERS[0]

    # 1 Local
    v = values.get("local", {})
    if v:
        o = template.safe_substitute(v)
        with open(Path(f".env"), "w") as f:
            f.write(o)

    if not OUTPUT_DIR.exists():
        OUTPUT_DIR.mkdir()

    now = datetime.now().isoformat(timespec="seconds")
    # 2 deployment
    for stage in STAGES:
        v = values.get(stage, {})
        if v:
            o = template.safe_substitute(v)

            file_path = OUTPUT_DIR / Path(f".env.{server}.{stage}")

            if file_path.exists():
                # Backup Raw files
                dst_dir = OUTPUT_DIR / Path(f"backup_{now}")
                print(
                    f"Already .env.{server}.{stage} exists. move file to {dst_dir} dir"
                )
                if not dst_dir.exists():
                    dst_dir.mkdir()
                shutil.move(file_path, dst_dir / file_path.name)

            print(f"Rendering .env.{server}.{stage} to {file_path}")
            with open(file_path, "w") as f:
                f.write(o)


if __name__ == "__main__":
    render_env_template()

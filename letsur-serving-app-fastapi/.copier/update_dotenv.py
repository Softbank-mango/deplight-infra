from pathlib import Path

import yaml

x = Path.home().name
# Update the .env file with the answers from the .copier-answers.yml file
# without using Jinja2 templates in the .env file, this way the code works as is
# without needing Copier, but if Copier is used, the .env file will be updated
root_path = Path(__file__).parent.parent
answers_path = Path(__file__).parent / ".copier-answers.yaml"
answers = yaml.safe_load(answers_path.read_text())
env_path = root_path / ".env.core"
env_content = env_path.read_text()
lines = []


LAMP_PROJECT_NAME = answers.get("LAMP_PROJECT_NAME", "letsur-serving-app")
LETSUR_ML_PROJECT_NAME = answers.get("LETSUR_ML_PROJECT_NAME")
LAMP_PROJECT_ID_KEY = "LAMP_PROJECT_ID"


# 호환 작업
if not LETSUR_ML_PROJECT_NAME:
    LETSUR_ML_PROJECT_NAME = LAMP_PROJECT_NAME

for line in env_content.splitlines():
    for key, value in answers.items():
        upper_key = key.upper()
        if line.startswith(f"{upper_key}="):
            if " " in value:
                content = f"{upper_key}={value!r}"
            else:
                content = f"{upper_key}={value}"
            new_line = line.replace(line, content)
            lines.append(new_line)
            break
    else:
        if line.startswith(f"{LAMP_PROJECT_ID_KEY}="):
            content = f"{LAMP_PROJECT_ID_KEY}={LETSUR_ML_PROJECT_NAME}-local"
            new_line = line.replace(line, content)
            lines.append(new_line)
        else:
            lines.append(line)

env_path.write_text("\n".join(lines))


### create .env file
env_path = root_path / ".env"
if not env_path.exists():
    env_path.touch()

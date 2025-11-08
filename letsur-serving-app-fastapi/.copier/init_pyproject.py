from pathlib import Path
import yaml
import re


root_path = Path(__file__).parent.parent
answers_path = Path(__file__).parent / ".copier-answers.yaml"
answers = yaml.safe_load(answers_path.read_text())

LAMP_PROJECT_NAME = answers.get("LAMP_PROJECT_NAME", "letsur-serving-app")
LETSUR_ML_PROJECT_NAME = answers.get("LETSUR_ML_PROJECT_NAME", "letsur-serving-app")


def update_pyproject_name(project_name: str):
    pyproject_path = Path("pyproject.toml")
    content = pyproject_path.read_text()

    # Use regex to find and replace the project name
    # This assumes the project name is defined as `name = "..."` under the `[project]` section
    updated_content = re.sub(
        r'(\[project\].*?^name\s*=\s*").*?(")',
        r"\g<1>" + project_name + r"\g<2>",
        content,
        flags=re.MULTILINE | re.DOTALL,
    )

    pyproject_path.write_text(updated_content)


if __name__ == "__main__":
    project_name_to_set = LETSUR_ML_PROJECT_NAME or LAMP_PROJECT_NAME
    update_pyproject_name(project_name_to_set)

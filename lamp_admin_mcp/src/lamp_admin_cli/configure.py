import click
import yaml
import logging
from rich.prompt import Prompt

from .settings import *
from .utils import masking_password

#console = Console()

def hello():
    print("World")
    return True

def configure(profile_name) -> Configure:
    
    with open(CONF_FILE, 'r') as f:
       origin_profiles = yaml.safe_load(f) or {}
    
    _p = origin_profiles.get(profile_name, {})
    
    text = "Update" if _p else "Create"
    text += f" profile: [red]{profile_name}[/red]"
    
    logging.info(text)
    
    lamp_environment = Prompt.ask('[green]LAMP_ENVIRONMENT', choices=LAMPStage.all_values(), default=LAMPStage.all_values()[0])
    databricks_token_default = _p.get("DATABRICKS_TOKEN")
    databricks_token_default_show = None
    if databricks_token_default:
        databricks_token_default_show = masking_password(databricks_token_default)
    databricks_token = Prompt.ask("[red]DATABRICKS_TOKEN", show_default=bool(databricks_token_default), default=databricks_token_default_show, password=True)
    
    if databricks_token == databricks_token_default_show:
        databricks_token = databricks_token_default

    if not (databricks_token):
        raise click.ClickException("No Inputs")
    
    github_auth_token_default = _p.get("GITHUB_AUTH_TOKEN")
    github_auth_token_default_show = None
    if github_auth_token_default:
        github_auth_token_default_show = masking_password(github_auth_token_default)
    github_auth_token = Prompt.ask("[red]GITHUB_AUTH_TOKEN", show_default=bool(github_auth_token_default), default=github_auth_token_default_show, password=True)
    
    if github_auth_token == github_auth_token_default_show:
        github_auth_token = github_auth_token_default

    if not (github_auth_token):
        logging.info("[red]No GITHUB AUTH TOKEN[/red]\nEndpoint Sepc Validation 및 Generation 기능을 사용할 수 없습니다.")
    
    if origin_profiles:
        origin_profiles.update({profile_name: {
            'LAMP_ENVIRONMENT': lamp_environment,
            'DATABRICKS_TOKEN': databricks_token,
            'GITHUB_AUTH_TOKEN': github_auth_token,
        }})
        profiles = origin_profiles
    else:
        profiles = {profile_name: {
            'LAMP_ENVIRONMENT': lamp_environment,
            'DATABRICKS_TOKEN': databricks_token,
            'GITHUB_AUTH_TOKEN': github_auth_token,
        }}
    with open(CONF_FILE, 'w+') as f:
        yaml.safe_dump(profiles, f)
        
    logging.info("Done")
    
    return Configure.from_dict(_profile_name=profile_name, **profiles[profile_name])

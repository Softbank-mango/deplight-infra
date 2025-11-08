from pathlib import Path
from typing import List, Optional, Union

from github import Auth, Github
from github.GithubException import GithubException
from github.GitRelease import GitRelease
from github.PaginatedList import PaginatedList
from github.Repository import Repository
import logging

from lamp_admin_cli.inhouse.endpoint_spec import (
    BaseEndpointSpec,
    EnvSpec,
    MetadataSpec,
    ValuesSpec,
)
from lamp_admin_cli.settings import Configure

ALL_VALUES_PATH = "charts/letsur-common-model/values.yaml"
AI_VALUES_PATH = "charts/letsur-common-model/values.ai.yaml"

class DummyRelease:
    def __init__(self, title, branch, html_url) -> None:
        self.title = title
        self.branch = branch
        self.html_url = html_url

additional_releases = [
    DummyRelease("develop", "develop", "https://github.com/letsur-dev/helm-charts/tree/develop"),
    DummyRelease("staging", "stg", "https://github.com/letsur-dev/helm-charts/tree/stg"),
    # For Dev
    # DummyRelease("MLOP-443/values.ai.yaml-generator", "https://github.com/letsur-dev/helm-charts/tree/MLOP-443/values.ai.yaml-generator"),
    ]


def generate_endpoint_spec(
    profile: Configure,
    output_dir: Path,
    chart_version=None,
    all_values: bool = False,
):

    h = HelmChart.from_auth_token(profile.GITHUB_AUTH_TOKEN)
    releases = list(h.get_releases())
    releases.extend(additional_releases) # type: ignore

    assert chart_version in list(map(lambda x: x.title, releases)), "No chart version matched"
    # values, metadata.yaml, .env
    
    if chart_version in list(map(lambda x: x.title, additional_releases)):
        chart_version = list(filter(lambda x: x.title == chart_version, additional_releases))[0].branch

    stage = profile.LAMP_ENVIRONMENT
    files: List[BaseEndpointSpec] = []
    # 1. metadata.{stage}.yaml
    files.append(MetadataSpec(stage=stage, render_kwargs={"chart_version": chart_version}))
    
    # 2. values
    try:
        values_body = h.get_helm_values(ref=chart_version, all=all_values)
        values = ValuesSpec(stage=stage, body=values_body)
    except GithubException as e:
        if not e.status == 404:
            raise e
        values = ValuesSpec(stage=stage)
    files.append(values)
    
    # 3. env
    # 3.1 apiServer
    files.append(EnvSpec(stage=stage, file_name_kwargs={"service": "apiServer"}))
    
    # TODO
    # triton은?
    
    for f in files:
        f.save(output_dir)
    return True


def create_git_release(
    profile: Configure,
    repo: Union[str, Repository],
    tag: str,
    name: str,
    target_commitish: str,
    prerelease: bool = False,
) -> GitRelease:
    """Create a GitHub release and update it immediately.

    Args:
        profile: Configure object containing GITHUB_AUTH_TOKEN and other settings.
        repo: Repository full name (e.g., "owner/name") or a Repository instance.
        tag: Release tag (e.g., "v1.2.3").
        name: Release name (title).
        target_commitish: Commitish or branch to create the tag on.
        body: Optional release notes.
        draft: Whether the release is a draft.
        prerelease: Whether the release is a pre-release.

    Returns:
        The created GitRelease object.
    """
    logging.debug("Creating GitHub release: repo=%s, tag=%s, name=%s, target=%s", repo, tag, name, target_commitish)
    github_client: Github = Github(auth=Auth.Token(profile.GITHUB_AUTH_TOKEN))
    repository: Repository
    if isinstance(repo, str):
        repository = github_client.get_repo(repo)
    else:
        repository = repo
    try:
        release: GitRelease = repository.create_git_release(
            tag=tag,
            name=name,
            message="lamp-MCP를 이용해 생성된 release draft",
            draft=True,
            prerelease=prerelease,
            target_commitish=target_commitish,
        )
        # Ensure fields are set as desired; also demonstrates update usage.
        release.update_release(
            name=name,
            message="lamp-MCP를 이용해 생성된 release",
            draft=False,
            prerelease=prerelease,
            tag_name=tag,
            target_commitish=target_commitish,
        )
        logging.info("Created and updated release '%s' (%s)", name, release.html_url)
        return release
    except GithubException as e:
        logging.error("Failed to create/update release: %s", e)
        raise


def list_repo_tag_names(
    profile: Configure,
    repo: Union[str, Repository],
) -> List[str]:
    """Return all tag names of a repository as a list of strings.

    If `repo` is a string ("owner/name"), it resolves it using the
    provided `profile`'s GitHub token. If it's a Repository instance,
    it uses it directly.
    """
    github_client: Github = Github(auth=Auth.Token(profile.GITHUB_AUTH_TOKEN))
    repository: Repository
    if isinstance(repo, str):
        repository = github_client.get_repo(repo)
    else:
        repository = repo

    try:
        tags = repository.get_tags()
        return [t.name for t in tags]
    except GithubException as e:
        logging.error("Failed to fetch tags: %s", e)
        raise


class HelmChart:
    repo_path = "letsur-dev/helm-charts"
    
    def __init__(self, auth_token):
        self.github_client: Github = Github(auth=Auth.Token(auth_token))
        self.repo: Repository = self.github_client.get_repo(self.repo_path)
        
    @classmethod
    def from_auth_token(cls, auth_token: str):
        return HelmChart(auth_token=auth_token)
    
    def _get_contents(self, path: str, ref: str) -> bytes:
        return self.repo.get_contents(path=path, ref=ref).decoded_content # type: ignore
    
    def get_releases(self) -> PaginatedList[GitRelease]:
        return self.repo.get_releases()
    
    def get_helm_values(self, ref, all: bool = False):
        if all:
            return self._get_contents(path=ALL_VALUES_PATH, ref=ref).decode()
        return self._get_contents(path=AI_VALUES_PATH, ref=ref).decode()
    

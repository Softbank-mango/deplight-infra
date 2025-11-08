from typing import TYPE_CHECKING

from s3fs import S3FileSystem

from src._core.dataclasses.file.base import FileContent
from src._core.settings import celery_settings

from .base import FileUploader

# TODO
# 처음엔 celery꺼 쓰기로.
# 필요 시 분리.

if TYPE_CHECKING:
    from .base import LetsurFileModel

# s3_client = S3FileSystem(
#     anon=False,
#     endpoint_url=celery_settings.CELERY_BROKER_HOST,
#     key=celery_settings.AWS_ACCESS_KEY_ID,
#     secret=celery_settings.AWS_SECRET_ACCESS_KEY,
# )


class S3FileUploader(FileUploader):
    domain: str = celery_settings.CELERY_S3_DOMAIN
    root_dir = celery_settings.CELERY_S3_BUCKET

    def __init__(self, client: S3FileSystem | None = None):
        self.client: S3FileSystem = client or self._get_client()

    def upload_file(self, file: FileContent, sub_dir: str):
        path = self.get_file_path(file, sub_dir)
        if not self.client.exists(path):
            with self.client.open(
                path, "wb", s3_additional_kwargs={"ContentType": file.mime_type}
            ) as f:
                f.write(file.content)  # type: ignore

    def get_file_url(self, file: FileContent, sub_dir: str, **kwargs):
        return "/".join([f"https://{self.domain}", sub_dir, file.full_name])

    def get_file_path(self, file: FileContent, sub_dir: str):
        return "/".join([self.root_dir, sub_dir, file.full_name])

    def _get_client(self, **kwargs) -> S3FileSystem:
        return S3FileSystem(
            anon=False,
            endpoint_url=celery_settings.CELERY_S3_ENDPOINT_URL,
            key=celery_settings.AWS_ACCESS_KEY_ID,
            secret=celery_settings.AWS_SECRET_ACCESS_KEY,
            skip_instance_cache=True,
            **kwargs,
        )

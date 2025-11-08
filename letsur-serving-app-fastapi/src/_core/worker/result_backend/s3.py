import botocore
from celery.backends.s3 import S3Backend
from kombu.utils.encoding import bytes_to_str
from s3fs import S3FileSystem

from src._core.logger import ServingLogger

from .dataclasses import LetsurTask, LetsurTaskResult

# from src._core.settings import app_settings


CONTENT_TYPE_JSON = "application/json"


class LetsurS3Backend(S3Backend):
    task_keyprefix = "task"
    group_keyprefix = "taskset"
    chord_keyprefix = "chord"
    # project_id = app_settings.LAMP_PROJECT_ID

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.domain = self.app.conf.get("s3_domain", None)
        self.s3fs = S3FileSystem(
            endpoint_url=self.endpoint_url,
            key=self.aws_access_key_id,
            secret=self.aws_secret_access_key,
            asynchronous=True,
        )

    def get_public_url(self, task_id):
        key = bytes_to_str(self.get_key_for_task(task_id=task_id))
        key_bucket_path = self.base_path + key if self.base_path else key
        if self.domain:
            return f"https://{self.domain}/{key_bucket_path}"
        bucket = self._s3_resource.Bucket(name=self.bucket_name)
        url = bucket.meta.client.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket_name, "Key": key_bucket_path}
        )
        return url

    def _get_key_for(self, prefix, id, key=""):
        key_t = self.key_t
        ret = key_t("/").join(
            [
                prefix,
                key_t(id),
                key_t(key),
            ]
        )
        return ret.rstrip(b"/")

    def _get_s3_url(self, key):
        key_bucket_path = self.base_path + key if self.base_path else key
        return f"s3://{self.bucket_name}/{key_bucket_path}"

    async def init_task(self, task_id):
        key = bytes_to_str(self.get_key_for_task(task_id=task_id))
        path = self._get_s3_url(key)
        # Task_ID가 겹치는 케이스는 무시하기로.
        await self.s3fs._touch(path, ContentType=CONTENT_TYPE_JSON)

    def start_task(self, task_id):
        key = bytes_to_str(self.get_key_for_task(task_id=task_id))
        s3_object = self._get_s3_object(key)
        ServingLogger().debug(f"start task: {s3_object.bucket_name}, {s3_object.key}")
        task = LetsurTask(
            state="START",
        )
        s3_object.put(
            Body=task.model_dump_json().encode(), ContentType=CONTENT_TYPE_JSON
        )

    def end_task(self, task_id, result: LetsurTaskResult):
        key = bytes_to_str(self.get_key_for_task(task_id=task_id))
        s3_object = self._get_s3_object(key)
        ServingLogger().debug(f"end task: {s3_object.bucket_name}, {s3_object.key}")
        task = LetsurTask(state="END", result=result)
        s3_object.put(
            Body=task.model_dump_json().encode(), ContentType=CONTENT_TYPE_JSON
        )

    def error_task(self, task_id, result: LetsurTaskResult):
        key = bytes_to_str(self.get_key_for_task(task_id=task_id))
        s3_object = self._get_s3_object(key)
        task = LetsurTask(state="ERROR", result=result)
        s3_object.put(
            Body=task.model_dump_json().encode(), ContentType=CONTENT_TYPE_JSON
        )

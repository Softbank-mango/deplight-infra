import base64
import hashlib
import inspect
import mimetypes
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, ClassVar, Generic, Optional, Type, TypeVar, cast

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema
from typing_extensions import get_args, get_origin

import pylibmagic  # isort:skip
import magic  # isort:skip


def _get_md5hash(obj: bytes):
    hash_object = hashlib.md5(obj)
    return hash_object.hexdigest()


def _guess_filetype(content: bytes) -> tuple[str, str | None]:
    """
    binary의 시그니쳐를 기반으로, 파일의 mime_type과 extension을 유추해주는 method.
    유추에 실패하는 경우 ("", "")를 반환합니다.
    """
    mime_type = magic.from_buffer(content, mime=True)
    file_extension = mimetypes.guess_extension(mime_type)
    return (mime_type, file_extension)


@dataclass
class FileContent:
    content: bytes
    extension: Optional[str] = None
    mime_type: Optional[str] = None
    file_name: str = field(init=False)

    def __post_init__(self):
        self.file_name = _get_md5hash(self.content)
        if not (self.extension and self.mime_type):
            mime_type, extension = _guess_filetype(self.content)
            self.extension = self.extension or extension
            self.mime_type = self.mime_type or mime_type
        if self.extension and self.extension.startswith("."):
            self.extension = self.extension[1:]

    @property
    def full_name(self) -> str:
        return (
            self.file_name + "." + self.extension if self.extension else self.file_name
        )


### FileUploader
class FileUploader(ABC):
    @abstractmethod
    def get_file_url(self, file: FileContent, **kwargs) -> str:
        raise NotImplementedError

    @abstractmethod
    def upload_file(self, file: FileContent, **kwargs):
        raise NotImplementedError


class LetsurFileMIMEType(str, Enum):
    PNG = "image/png"


class LetsurFileReturnType(str, Enum):
    BASE64 = "base64"
    URL = "url"


FileType = TypeVar("FileType")


class LetsurFileModel(Generic[FileType]):
    """
    extension: str, 파일 확장자; 없을 시 bytes 기반 타입 추론
    mime_type: LetsurFileMIMEType 사용 or (MIME_TYPE:str) 주입;  None일 시 extension 기반 타입 추론
    object_cls: BaseModel instance에 주입할 python instance class
    json_return_type: response를 위해 json으로 convert될 때 변경될 타입.
                        LetsurFileReturnType.BASE64 : Base64 encoding string으로 제공
                        LetsurFileReturnType.URL : public S3 업로드 후 S3 url 제공


    def to_bytes(self, obj):
        메서드 작성 필요.
        python file object를 response로 return하기 위해 bytes로 변환하는 method

    e.g.

    class PILImageBody(LetsurFileModel[Image]):
        file_type = LetsurFileMIMEType.PNG
        extension = "png"
        object_cls = Image
        json_return_type = LetsurFileReturnType.URL

    def to_bytes(self, obj: Image) -> bytes:
        # object instance를 S3 Body bytes로 만드는 코드
        stream = io.BytesIO()
        obj.save(stream, "PNG")
        stream.seek(0)
        ret = stream.read()
        stream.close()
        return ret
    """

    extension: ClassVar[Optional[str]] = None
    file_type: ClassVar[Optional[str]] = None
    object_cls: ClassVar[Callable]
    json_return_type: ClassVar[LetsurFileReturnType] = LetsurFileReturnType.URL

    from .s3_uploader import S3FileUploader

    file_uploader: ClassVar[Type[FileUploader]] = S3FileUploader

    def __init__(self, obj: FileType):
        self._obj: FileType = obj
        self._dt = datetime.now(timezone.utc).strftime("%Y%m%d")

    def __repr__(self) -> str:
        return f"{super().__repr__()}:({self._obj})"

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:

        origin = get_origin(source_type)
        if origin is None:  # used as `x: LetsurFileModel` without params
            origin = source_type
            item_tp = Any
        else:
            item_tp = get_args(source_type)[0]

        item_schema = handler.generate_schema(item_tp)
        assert issubclass(cls.file_uploader, FileUploader) and not inspect.isabstract(
            cls.file_uploader
        ), f"{cls}에 FileUploader를 상속 받은 file_uploader cls를 할당해야 합니다."

        def python_serialization(value: FileType) -> FileType:
            return value

        def json_serialization(value: FileType) -> str:
            file_model: LetsurFileModel = source_type(value)
            f = file_model.to_file_content()
            if file_model.json_return_type == LetsurFileReturnType.BASE64:
                return base64.b64encode(f.content).decode("utf-8")
            elif file_model.json_return_type == LetsurFileReturnType.URL:
                uploader = file_model.file_uploader()
                uploader.upload_file(f, sub_dir=file_model._dt)
                return uploader.get_file_url(f, sub_dir=file_model._dt)
            else:
                raise ValueError(f"json_return_type 미정: {file_model}:{value}")

        def last_serialization(value, handler, info) -> FileType | str:
            if info.mode == "json":
                return json_serialization(value)
            return python_serialization(value)

        def validate_json_file_val(value: str) -> FileType:
            # TODO
            # bytes or url -> python object
            return value  # type: ignore

        def validate_python_file_val(value: FileType) -> FileType:
            return value

        json_schema = core_schema.chain_schema(
            [
                core_schema.str_schema(),
                core_schema.no_info_before_validator_function(
                    validate_json_file_val,
                    item_schema,
                    serialization=core_schema.plain_serializer_function_ser_schema(
                        json_serialization
                    ),
                ),
            ]
        )

        python_schema = core_schema.chain_schema(
            [
                core_schema.is_instance_schema(cls.object_cls),
                core_schema.no_info_before_validator_function(
                    validate_python_file_val,
                    item_schema,
                    serialization=core_schema.plain_serializer_function_ser_schema(
                        python_serialization
                    ),
                ),
            ]
        )

        return core_schema.json_or_python_schema(
            # for JSON accept an object with name and item keys
            json_schema=json_schema,
            python_schema=python_schema,
            serialization=core_schema.wrap_serializer_function_ser_schema(
                last_serialization, info_arg=True
            ),
        )

    @abstractmethod
    def to_bytes(self, obj: FileType) -> bytes:
        """
        object_cls의 인스턴스 python object obj를 bytes로 변환하는 로직을 채우세요.
        """
        raise NotImplementedError()

    def to_file_content(self) -> FileContent:
        return FileContent(
            content=self.to_bytes(self._obj),
            extension=self.extension,
            mime_type=self.file_type,
        )

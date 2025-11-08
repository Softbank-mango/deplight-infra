import io

from PIL.Image import Image

from .base import LetsurFileMIMEType, LetsurFileModel, LetsurFileReturnType
from .s3_uploader import S3FileUploader


class PILImageBody(LetsurFileModel[Image]):
    extension = "png"
    object_cls = Image
    json_return_type = LetsurFileReturnType.URL
    file_type = LetsurFileMIMEType.PNG
    file_uploader = S3FileUploader

    def to_bytes(self, obj: Image) -> bytes:
        # object instance를 S3 Body bytes로 만드는 코드
        stream = io.BytesIO()
        obj.save(stream, "PNG")
        stream.seek(0)
        ret = stream.read()
        stream.close()
        return ret

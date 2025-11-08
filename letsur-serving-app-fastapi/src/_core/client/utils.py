from importlib.util import find_spec

# https://github.com/huggingface/diffusers/blob/main/src/diffusers/utils/import_utils.py#L196

_available_triton_client = find_spec("tritonclient") is not None


def is_triton_client_available():
    return _available_triton_client


_available_httpx_client = find_spec("httpx") is not None


def is_httpx_client_availiable():
    return _available_httpx_client

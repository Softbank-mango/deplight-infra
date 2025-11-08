import numpy as np
import tritonclient.grpc as grpclient
from pydantic_settings import BaseSettings
from tritonclient.grpc.aio import InferenceServerClient
from tritonclient.utils import triton_to_np_dtype
from typing_extensions import TYPE_CHECKING, List, Optional, Tuple

from src._core.logger import ServingLogger

from .triton import triton_settings

# TODO
# class로 fastapi_app에서 쓰는게 나은 듯

triton_client = InferenceServerClient(
    url=f"{triton_settings.triton_host}:{triton_settings.triton_port}"
)


async def reload(model_name):
    await triton_client.load_model(model_name=model_name)


async def is_model_ready(model_name):
    return await triton_client.is_model_ready(model_name=model_name)


async def is_server_ready():
    return await triton_client.is_server_ready()


async def get_model_inputs_outputs(
    model_name: str, model_version: str = ""
) -> Tuple[List[grpclient.InferInput], List[grpclient.InferRequestedOutput]]:
    model_metadata = await triton_client.get_model_metadata(
        model_name=model_name, model_version=model_version
    )

    inputs = []
    outputs = []

    for input_ in model_metadata.inputs:
        inputs.append(
            grpclient.InferInput(
                name=input_.name, shape=input_.shape, datatype=input_.datatype
            )
        )

    for output_ in model_metadata.outputs:
        outputs.append(grpclient.InferRequestedOutput(name=output_.name))

    return inputs, outputs


def get_datatype_of_input_as_np(input: grpclient.InferInput):
    return triton_to_np_dtype(input.datatype())


def set_inputs_data_from_numpy(
    inputs: List[grpclient.InferInput], inputs_data: List[np.ndarray]
):
    new_inputs = []
    for input_tr_tensor, val in zip(inputs, inputs_data):
        dtype = get_datatype_of_input_as_np(input_tr_tensor)
        val = val.astype(dtype)
        input_tr_tensor = input_tr_tensor.set_shape(val.shape)
        input_tr_tensor.set_data_from_numpy(val)
        new_inputs.append(input_tr_tensor)
    return new_inputs


async def infer(
    model_name: str,
    inputs: List[grpclient.InferInput],
    outputs: List[grpclient.InferRequestedOutput],
    model_version: str = "",
) -> grpclient.InferResult:
    return await triton_client.infer(
        model_name=model_name,
        inputs=inputs,
        outputs=outputs,
        model_version=model_version,
    )

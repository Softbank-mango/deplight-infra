import numpy as np
import tritonclient.grpc as grpclient
from pydantic_settings import BaseSettings
from tritonclient.utils import triton_to_np_dtype
from typing_extensions import List, Optional, Tuple


class TritonSetttings(BaseSettings):
    triton_host: str = ""
    triton_port: int = 8002


triton_settings = TritonSetttings()

# TODO
# class로 fastapi_app에서 쓰는게 나은 듯

triton_client = grpclient.InferenceServerClient(
    url=f"{triton_settings.triton_host}:{triton_settings.triton_port}"
)


def reload(model_name):
    triton_client.unload_model(model_name=model_name)
    triton_client.load_model(model_name=model_name)


def is_model_ready(model_name):
    return triton_client.is_model_ready(model_name=model_name)


def is_server_ready():
    return triton_client.is_server_ready()


def get_model_inputs_outputs(
    model_name: str, model_version: str = ""
) -> Tuple[List[grpclient.InferInput], List[grpclient.InferRequestedOutput]]:
    model_metadata = triton_client.get_model_metadata(
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

    return inputs, outputs, model_metadata


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


def infer(
    model_name: str,
    inputs: List[grpclient.InferInput],
    outputs: List[grpclient.InferRequestedOutput],
    model_version: str = "",
) -> grpclient.InferResult:
    return triton_client.infer(
        model_name=model_name,
        inputs=inputs,
        outputs=outputs,
        model_version=model_version,
    )

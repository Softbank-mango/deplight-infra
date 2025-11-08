from src._core.dataclasses import InferInputs, InferOutputs
from src.dataclasses import ModelInput, ModelOutput


def test_get_openapi_json(client):
    x = client.get("/openapi.json")
    assert x.status_code == 200


def test_echo_invocations(client):
    data = InferInputs(inputs=[ModelInput()])

    ret = client.post("/invocations", json=data.model_dump())
    assert ret.status_code == 200
    assert InferOutputs(**ret.json())
    assert ret.json()["predictions"][0] == ModelOutput().model_dump()


# 나머진 귀찮타리..

import pytest

from ai_translator import config, ocr


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio("asyncio")
async def test_call_azure_read_missing_config(monkeypatch):
    monkeypatch.setattr(config, "AZURE_DI_ENDPOINT", None)
    monkeypatch.setattr(config, "AZURE_DI_API_KEY", None)
    monkeypatch.setattr(config, "AZURE_DI_API_VERSION", None)
    monkeypatch.setattr(config, "AZURE_DI_MODEL", None)

    with pytest.raises(ocr.StageError) as excinfo:
        await ocr.call_azure_read(b"data", "image/png", {})

    assert "Missing Azure Document Intelligence configuration" in excinfo.value.message
    for expected in ["AZURE_DI_ENDPOINT", "AZURE_DI_API_KEY", "AZURE_DI_API_VERSION", "AZURE_DI_MODEL"]:
        assert expected in excinfo.value.message


def test_build_stage_error_response_includes_fields():
    stages = {}
    response = ocr.build_stage_error_response("azure_read_call", "boom", stages)

    assert response["error_stage"] == "azure_read_call"
    assert response["error_message"] == "boom"
    assert response["stages"]["azure_read_call"]["status"] == "error"

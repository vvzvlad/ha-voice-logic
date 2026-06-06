import requests
from requests_toolbelt.multipart.encoder import MultipartEncoder

from src import stt_client
from src.settings import settings


class FakeResponse:
    def __init__(self, status_code, content=b"", text=""):
        self.status_code = status_code
        self.content = content
        self.text = text


def _build_multipart(with_file=True):
    """Build a real multipart body with a 'model' field and optionally a 'file'."""
    fields = {"model": "whisper-1"}
    if with_file:
        fields["file"] = ("audio.wav", b"RIFFdata", "audio/wav")
    enc = MultipartEncoder(fields=fields)
    return enc.to_string(), enc.content_type


def test_extract_file_part_returns_tuple():
    body, content_type = _build_multipart(with_file=True)
    filename, file_bytes, file_content_type = stt_client._extract_file_part(body, content_type)
    assert filename == "audio.wav"
    assert file_bytes == b"RIFFdata"
    assert file_content_type == "audio/wav"


def test_extract_file_part_without_file_returns_none():
    body, content_type = _build_multipart(with_file=False)
    assert stt_client._extract_file_part(body, content_type) is None


def test_transcribe_audio_without_file_returns_empty():
    body, content_type = _build_multipart(with_file=False)
    status, payload = stt_client.transcribe_audio(body, content_type)
    assert status == 200
    assert payload == b'{"text": ""}'


def test_transcribe_audio_success(monkeypatch):
    body, content_type = _build_multipart(with_file=True)

    def fake_post(*args, **kwargs):
        return FakeResponse(200, content=b'{"text":"\xd0\xbf\xd1\x80\xd0\xb8\xd0\xb2\xd0\xb5\xd1\x82"}')

    monkeypatch.setattr(stt_client.requests, "post", fake_post)

    status, payload = stt_client.transcribe_audio(body, content_type)
    assert status == 200
    assert payload == b'{"text":"\xd0\xbf\xd1\x80\xd0\xb8\xd0\xb2\xd0\xb5\xd1\x82"}'


def test_transcribe_audio_forces_params_and_auth(monkeypatch):
    body, content_type = _build_multipart(with_file=True)

    captured = {}

    def fake_post(*args, **kwargs):
        # Capture the outgoing request so we can assert on forced params/auth.
        captured.update(kwargs)
        return FakeResponse(200, content=b'{"text":"ok"}')

    monkeypatch.setattr(stt_client.requests, "post", fake_post)

    status, payload = stt_client.transcribe_audio(body, content_type)
    assert status == 200
    assert payload == b'{"text":"ok"}'

    # Incoming auth is ignored; our key from settings is used instead.
    assert captured["headers"]["Authorization"] == f"Bearer {settings.groq_api_key}"

    # Our params are forced, overriding any incoming values (e.g. the bogus model).
    assert captured["data"]["model"] == settings.groq_stt_model
    assert captured["data"]["language"] == "ru"
    assert captured["data"]["response_format"] == "json"
    assert captured["data"]["temperature"] == "0"

    # The file part is forwarded with its filename and bytes intact.
    file_tuple = captured["files"]["file"]
    assert file_tuple[0] == "audio.wav"
    assert file_tuple[1] == b"RIFFdata"


def test_transcribe_audio_request_exception(monkeypatch):
    body, content_type = _build_multipart(with_file=True)

    def fake_post(*args, **kwargs):
        raise requests.RequestException("boom")

    monkeypatch.setattr(stt_client.requests, "post", fake_post)

    status, payload = stt_client.transcribe_audio(body, content_type)
    assert status == 200
    assert payload == b'{"text": ""}'


def test_transcribe_audio_groq_non_200(monkeypatch):
    body, content_type = _build_multipart(with_file=True)

    def fake_post(*args, **kwargs):
        return FakeResponse(400, content=b"", text="bad")

    monkeypatch.setattr(stt_client.requests, "post", fake_post)

    status, payload = stt_client.transcribe_audio(body, content_type)
    assert status == 200
    assert payload == b'{"text": ""}'

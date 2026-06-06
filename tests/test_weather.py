from src import weather


class FakeResponse:
    def __init__(self, status_code, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def test_get_weather_summary_ok(monkeypatch):
    payload = {
        "main": {"temp": 12.3},
        "wind": {"speed": 3},
        "weather": [{"description": "ясно"}],
    }

    def fake_get(*args, **kwargs):
        return FakeResponse(200, payload)

    monkeypatch.setattr(weather.requests, "get", fake_get)

    result = weather.get_weather_summary("Moscow", "key")
    assert "12 градусов" in result
    assert "ясно" in result
    assert "ветер 3 метров в секунду" in result


def test_get_weather_summary_error(monkeypatch):
    def fake_get(*args, **kwargs):
        return FakeResponse(500, text="server error")

    monkeypatch.setattr(weather.requests, "get", fake_get)

    assert weather.get_weather_summary("Moscow", "key") is None

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


def test_get_weather_summary_passes_proxy(monkeypatch):
    payload = {
        "main": {"temp": 1},
        "wind": {"speed": 0},
        "weather": [{"description": "ясно"}],
    }
    captured = {}

    def fake_get(*args, **kwargs):
        captured["proxies"] = kwargs.get("proxies")
        return FakeResponse(200, payload)

    monkeypatch.setattr(weather.requests, "get", fake_get)

    weather.get_weather_summary("Moscow", "key", "socks5h://10.0.0.1:1080")
    assert captured["proxies"] == {
        "https": "socks5h://10.0.0.1:1080",
        "http": "socks5h://10.0.0.1:1080",
    }


def test_get_weather_summary_no_proxy(monkeypatch):
    payload = {
        "main": {"temp": 1},
        "wind": {"speed": 0},
        "weather": [{"description": "ясно"}],
    }
    captured = {}

    def fake_get(*args, **kwargs):
        captured["proxies"] = kwargs.get("proxies")
        return FakeResponse(200, payload)

    monkeypatch.setattr(weather.requests, "get", fake_get)

    weather.get_weather_summary("Moscow", "key")
    assert captured["proxies"] is None

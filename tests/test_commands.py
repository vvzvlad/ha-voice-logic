from src import commands


def test_extract_command_blocks_multiple():
    text = "<command>a:on</command> mid <command>b:off</command>"
    assert commands.extract_command_blocks(text) == ["a:on", "b:off"]


def test_extract_command_blocks_case_insensitive():
    text = "<COMMAND>a:on</COMMAND>"
    assert commands.extract_command_blocks(text) == ["a:on"]


def test_extract_command_blocks_multiline():
    text = "<command>a:on\nmore</command>"
    assert commands.extract_command_blocks(text) == ["a:on\nmore"]


def test_parse_command_payload_on():
    assert commands.parse_command_payload("room_light:on") == {
        "device_id": "room_light",
        "value": "on",
    }


def test_parse_command_payload_numeric():
    assert commands.parse_command_payload("room_ac:22") == {
        "device_id": "room_ac",
        "value": "22",
    }


def test_parse_command_payload_garbage():
    assert commands.parse_command_payload("not a valid command !!!") is None


def test_process_commands_in_content(monkeypatch):
    calls = []

    def fake_post(*args, **kwargs):
        calls.append((args, kwargs))
        return None

    monkeypatch.setattr(commands.requests, "post", fake_post)

    content = "<command>room_light:on</command><command>room_ac:22</command>"
    result = commands.process_commands_in_content(content)

    assert len(calls) == 2
    assert result == [
        {"device_id": "room_light", "value": "on"},
        {"device_id": "room_ac", "value": "22"},
    ]

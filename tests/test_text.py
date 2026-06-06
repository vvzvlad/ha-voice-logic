import pytest

from src.text import extract_request_text, processing_response


def test_extract_request_text_valid():
    payload = {"request": {"text": "включи свет"}}
    assert extract_request_text(payload) == "включи свет"


def test_extract_request_text_request_not_dict():
    with pytest.raises(ValueError):
        extract_request_text({"request": "not-a-dict"})


def test_extract_request_text_text_not_str():
    with pytest.raises(ValueError):
        extract_request_text({"request": {"text": 123}})


def test_processing_response_strips_think():
    result = processing_response("<think>internal</think>hello")
    assert "internal" not in result
    assert "<think>" not in result
    assert result == "hello"


def test_processing_response_strips_command():
    result = processing_response("text<command>room_light:on</command>")
    assert "room_light:on" not in result
    assert "<command>" not in result
    assert result == "text"


def test_processing_response_replacements():
    assert processing_response("50%") == "50процентов"
    assert processing_response("5 м/с") == "5 метров в секунду"


def test_processing_response_trims():
    assert processing_response("   spaced   ") == "spaced"

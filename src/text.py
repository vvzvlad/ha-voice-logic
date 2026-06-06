"""Request text extraction and response post-processing."""

import re


def extract_request_text(json_data):
    """Strictly extract request.text (string) from expected schema.

    Expected schema:
    {
        "request": { "text": str, "source": str? },
        "device": { "id": str? }?
    }
    """
    req = json_data.get("request")
    if not isinstance(req, dict):
        raise ValueError("Invalid payload: 'request' must be an object")
    text = req.get("text")
    if not isinstance(text, str):
        raise ValueError("Invalid payload: 'request.text' must be a string")
    return text


def processing_response(response):
    # Remove <think>...</think> and <command>...</command> tags and their response
    response = re.sub(r'<think>.*?</think>', '', response, flags=re.DOTALL)
    response = re.sub(r'<command>.*?</command>', '', response, flags=re.DOTALL)
    response = response.strip()

    response = response.replace("что", "што")
    response = response.replace("чтобы", "штобы")
    response = response.replace("конечно", "конешно")
    response = response.replace("°С", "градусов")
    response = response.replace("%", "процентов")
    response = response.replace("м/с", "метров в секунду")
    return response

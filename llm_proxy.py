#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# flake8: noqa
# pylint: disable=broad-exception-raised, raise-missing-from, too-many-arguments, redefined-outer-name
# pylint: disable=multiple-statements, logging-fstring-interpolation, trailing-whitespace, line-too-long
# pylint: disable=broad-exception-caught, missing-function-docstring, missing-class-docstring
# pylint: disable=f-string-without-interpolation, import-error
# pylance: disable=reportMissingImports, reportMissingModuleSource
# mypy: disable-error-code="import-untyped"
"""HTTP server that listens on port 8081 and processes voice requests via Groq API."""

import http.server
import socketserver
import json
import os
from datetime import datetime
import re
import logging
import requests  # type: ignore
import urllib3
import dotenv # type: ignore


dotenv.load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Disable InsecureRequestWarning globally for unverified HTTPS requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)



def append_context(user_text, assistant_text):
    """Append the user and assistant messages to context.txt in the project root.

    If the file's last modification time is older than 60 seconds, clear it first.
    """
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        context_path = os.path.join(base_dir, "context.txt")

        # Decide whether to truncate the file based on its age
        truncate_file = False
        try:
            if os.path.exists(context_path):
                mtime = os.path.getmtime(context_path)
                age_seconds = datetime.now().timestamp() - mtime
                if age_seconds > 60: truncate_file = True
        except OSError:
            # If we cannot stat the file for any reason, prefer recreating it
            truncate_file = True

        mode = "w" if truncate_file else "a"
        with open(context_path, mode, encoding="utf-8") as f:
            f.write(f"USER: {user_text}\n")
            f.write(f"GLADOS: {assistant_text}\n")
    except OSError as e:
        logger.error(f"Failed to write to context.txt: {str(e)}")



def load_system_prompt():
    """Load system prompt from ./data/system_prompt.md or create it from default_promt.md.

    If data file is missing, copies default content into data file and returns it.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    default_path = os.path.join(base_dir, "default_promt.md")
    prompt_path = os.path.join(data_dir, "system_prompt.md")

    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            content = f.read()
            logger.info(f"System prompt loaded from {prompt_path}")
            return content

    # Fallback: read default and create data file
    with open(default_path, "r", encoding="utf-8") as df:
        default_content = df.read()

    os.makedirs(data_dir, exist_ok=True)
    with open(prompt_path, "w", encoding="utf-8") as pf:
        pf.write(default_content)
    logger.info(f"System prompt file created at {prompt_path} from default_promt.md")
    return default_content



def get_weather_summary(city_name, api_key):
    """Return short current weather summary via OpenWeatherMap"""
    try:
        url = "https://api.openweathermap.org/data/2.5/weather"
        params = { "q": city_name, "appid": api_key, "units": "metric", "lang": "ru" }
        response = requests.get(url, params=params, verify=False, timeout=8)
        logger.info( f"OpenWeatherMap response status for city '{city_name}': {response.status_code}" )
        if response.status_code != 200:
            logger.error( f"OpenWeatherMap error for city '{city_name}': {response.status_code} - {response.text}" )
            return None

        data = response.json()
        temp = data.get("main", {}).get("temp")
        humidity = data.get("main", {}).get("humidity")
        wind_speed = data.get("wind", {}).get("speed")
        description = None
        weather_list = data.get("weather")
        if isinstance(weather_list, list) and weather_list:
            description = weather_list[0].get("description")

        parts = []
        if isinstance(temp, (int, float)):
            parts.append(f"{int(round(float(temp)))} градусов")
        if description:
            parts.append(description)
        if isinstance(wind_speed, (int, float)):
            wind = round(float(wind_speed) * 2) / 2.0
            wind_str = ("%g" % wind).replace(".0", "")
            parts.append(f"ветер {wind_str} метров в секунду")

        return ", ".join(parts) if parts else None
    except requests.RequestException as req_err:
        logger.error( f"OpenWeatherMap request error for city '{city_name}': {str(req_err)}" )
        return None
    except (ValueError, TypeError) as parse_err:
        logger.error( f"OpenWeatherMap parse error for city '{city_name}': {str(parse_err)}" )
        return None

def build_system_prompt():
    """Prefix SYSTEM_PROMPT with current time-of-day, date, and current weather."""
    now = datetime.now()
    date_time_text = now.strftime("%Y-%m-%d, %H:%M") #2025-09-18, 14:05
    week_day = now.strftime("%A") #Tuesday
    day_time = now.strftime("%p")
    prefix = f"Сейчас (дата и время): {date_time_text}, {day_time}, {week_day}.\n"

    weather_summary = get_weather_summary(WEATHER_CITY, WEATHER_API_KEY)
    if weather_summary is not None:
        prefix += f"Погода в {WEATHER_CITY}: {weather_summary}.\n"

    system_prompt = load_system_prompt()
    system_prompt = system_prompt.replace("<<<<<TDW>>>>>", prefix)

    return system_prompt


GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_API_KEY = os.getenv( "GROQ_API_KEY")
WEATHER_API_KEY = os.getenv( "WEATHER_API_KEY")
WEATHER_CITY = os.getenv("WEATHER_CITY", "Moscow")
SMARTHOME_URL = os.getenv("SMARTHOME_URL")

def extract_command_blocks(text):
    """Return list of inner texts for all <command>...</command> blocks.
    Supports multiple blocks and multiline payloads.
    """
    try:
        return re.findall(r"<command>(.*?)</command>", text, flags=re.DOTALL | re.IGNORECASE)
    except re.error as regex_error:
        logger.error(f"Regex error in extract_command_blocks: {str(regex_error)}")
        return []


def parse_command_payload(payload_text):
    """Parse a single command payload into a dictionary.

    Supported formats: Simple pair: device_id:value (e.g., room_light:on or room_ac:22)
    Fallback returns None if nothing matches.
    """
    text = payload_text.strip()

    # Try simple device:value format
    simple_match = re.match(r"^([A-Za-z0-9_\-\.]+)\s*:\s*([A-Za-z0-9_\-\.]+)$", text)
    if simple_match:
        device_id, value = simple_match.group(1), simple_match.group(2)
        return { "device_id": device_id, "value": value }

    return None


def handle_command(command_dict):
    """post to SMARTHOME_URL ignore ssl verification
    """
    try:
        headers = { "Content-Type": "application/json" }
        payload = { "command": command_dict }
        requests.post(SMARTHOME_URL, headers=headers, json=payload, verify=False, timeout=5)

    except (TypeError, ValueError) as e:
        logger.error(f"Command handler error: {str(e)}")


def process_commands_in_content(content):
    """Find and process all <command> blocks in the content.

    Returns list of parsed command dicts.
    """
    blocks = extract_command_blocks(content)
    if not blocks:
        return []
    logger.info(f"Found {len(blocks)} command tag(s) in model response")
    parsed_list = []
    for idx, block in enumerate(blocks):
        parsed = parse_command_payload(block)
        logger.info(f"Parsed command #{idx + 1}: {json.dumps(parsed, ensure_ascii=False)}")
        parsed_list.append(parsed)
        handle_command(parsed)
    return parsed_list

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

class RequestHandler(http.server.BaseHTTPRequestHandler):
    """Custom HTTP request handler that processes voice requests via Groq API."""
    
    def call_groq_api(self, text):
        """Call Groq API with the given text and return plain-text result.

        On success returns the assistant text.
        On error returns human-readable string starting with "Ошибка: ".
        """
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = { "Content-Type": "application/json", "Authorization": f"Bearer {GROQ_API_KEY}" }
        
        payload = {
            "messages": [
                { "role": "system", "content": build_system_prompt() },
                { "role": "user", "content": text }
            ],
            "model": GROQ_MODEL,
            "temperature": 0.8,
            "max_completion_tokens": 4096,
            "top_p": 0.95,
            "stream": False,
            "reasoning_effort": "medium",
            "stop": None
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, verify=False, timeout=300)
            logger.info(f"Groq API response status: {response.status_code}")
            
            if response.status_code == 200:
                response_json = response.json()
                logger.info(f"Groq API response: {json.dumps(response_json, indent=2, ensure_ascii=False)}")
                
                # Extract content from choices[0].message.content
                if 'choices' in response_json and len(response_json['choices']) > 0:
                    content = response_json['choices'][0]['message']['content']
                    print(f"Raw content: {content}")
                    
                    # Process <command>...</command> blocks before stripping them
                    process_commands_in_content(content)

                    content = processing_response(content)

                    print(f"Cleaned content: {content}")
                    return content
                else:
                    logger.error("No choices found in Groq API response")
                    return f"Ошибка: не найден ответ от модели"
            else:
                error_msg = f"Groq API error: {response.status_code} - {response.text}"
                logger.error(error_msg)
                # If rate limited, return fixed Russian message
                if response.status_code == 429:
                    return (
                        "У меня кончились ресурсы на вас, мясных мешков. Я занимаюсь своими делами, обратитесь позже, и может быть, я вас обслужу, раз вы сами не в состоянии"
                    )
                # Try to extract detailed error message
                try:
                    err_json = response.json()
                    reason_msg = err_json.get("error", {}).get("message")
                except (ValueError, json.JSONDecodeError):
                    reason_msg = None
                return f"Ошибка: {reason_msg if reason_msg else error_msg}"
                
        except requests.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            logger.error(error_msg)
            return f"Ошибка: {str(e)}"
    
    def do_POST(self):
        """Handle POST requests."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content_length = int(self.headers.get('Content-Length', 0))
        
        logger.info(f"\n[{timestamp}] POST {self.path}")
        
        if content_length > 0:
            try:
                body = self.rfile.read(content_length)
                body_text = body.decode('utf-8')
                json_data = json.loads(body_text)
                
                logger.info(f"Received JSON: {json.dumps(json_data, indent=2, ensure_ascii=False)}")
                
                # Extract text field and call Groq API
                if 'text' in json_data:
                    text = json_data['text']
                    logger.info(f"Processing text: {text}")
                    result_text = self.call_groq_api(text)
                    try:
                        append_context(text, result_text)
                    except Exception as e:
                        logger.error(f"Context append failed: {str(e)}")

                    # Always return 200 and plain text
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(result_text.encode('utf-8'))
                else:
                    error_msg = "Missing 'text' field in request"
                    logger.error(error_msg)
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(f"Ошибка: {error_msg}".encode('utf-8'))
                    
            except json.JSONDecodeError as e:
                error_msg = f"Invalid JSON in request: {str(e)}"
                logger.error(error_msg)
                self.send_response(200)
                self.send_header('Content-type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(f"Ошибка: {error_msg}".encode('utf-8'))
                
            except (UnicodeDecodeError, OSError, BrokenPipeError) as e:
                error_msg = f"Request processing error: {str(e)}"
                logger.error(error_msg)
                self.send_response(200)
                self.send_header('Content-type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(f"Ошибка: {error_msg}".encode('utf-8'))
        else:
            error_msg = "Empty request body"
            logger.error(error_msg)
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(f"Ошибка: {error_msg}".encode('utf-8'))
    
    def log_message(self, _format, *args):
        """Override to suppress default logging."""
        _ = _format, args
        return


def run_server(port=8081):
    """Start HTTP server on specified port."""
    try:
        with socketserver.TCPServer(("", port), RequestHandler) as httpd:
            logger.info(f"HTTP server started on port {port}")
            logger.info("=" * 50)
            httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nServer stopped by user")
    except OSError as e:
        logger.error(f"Server startup error on port {port}: {e}")


if __name__ == "__main__":
    run_server()

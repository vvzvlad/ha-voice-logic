"""HTTP server that processes voice requests via Groq API."""

import http.server
import socketserver
import json
import logging
from datetime import datetime

import urllib3

from src.settings import settings
from src.groq_client import call_groq_api
from src.stt_client import transcribe_audio
from src.text import extract_request_text
from src.context import append_context

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)

# Disable InsecureRequestWarning globally for unverified HTTPS requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class RequestHandler(http.server.BaseHTTPRequestHandler):
    """Custom HTTP request handler that processes voice requests via Groq API."""

    def do_POST(self):
        """Handle POST requests."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content_length = int(self.headers.get('Content-Length', 0))

        logger.info(f"\n[{timestamp}] POST {self.path}")

        # Route: OpenAI-compatible STT proxy to Groq Whisper.
        # Match by path suffix so it works regardless of any prefix the
        # caller prepends (e.g. /v1/audio/transcriptions).
        if self.path.endswith("/audio/transcriptions"):
            self._handle_transcription(content_length)
            return

        if content_length > 0:
            try:
                body = self.rfile.read(content_length)
                body_text = body.decode('utf-8')
                json_data = json.loads(body_text)

                logger.info(f"Received JSON: {json.dumps(json_data, indent=2, ensure_ascii=False)}")

                # Extract text field and call Groq API
                try:
                    text = extract_request_text(json_data)
                    logger.info(f"Processing text: {text}")
                    result_text = call_groq_api(text)
                    try:
                        append_context(text, result_text)
                    except Exception as e:
                        logger.error(f"Context append failed: {str(e)}")

                    # Always return 200 and plain text
                    self.send_response(200)
                    self.send_header('Content-type', 'text/plain; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(result_text.encode('utf-8'))
                except ValueError as ve:
                    error_msg = str(ve)
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

    def _handle_transcription(self, content_length):
        """Forward a multipart STT request to Groq Whisper and return its JSON."""
        try:
            body = self.rfile.read(content_length) if content_length > 0 else b""
            content_type = self.headers.get("Content-Type", "")
            status, payload = transcribe_audio(body, content_type)
        except (OSError, BrokenPipeError) as e:
            # Reading the request body failed; degrade gracefully.
            logger.error(f"STT request read error: {str(e)}")
            status, payload = 200, b'{"text": ""}'

        self.send_response(status)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        try:
            self.wfile.write(payload)
        except BrokenPipeError:
            pass

    def log_message(self, _format, *args):
        """Override to suppress default logging."""
        _ = _format, args
        return


def run_server(port=None):
    """Start HTTP server on specified port."""
    if port is None:
        port = settings.port
    try:
        with socketserver.TCPServer(("", port), RequestHandler) as httpd:
            logger.info(f"HTTP server started on port {port}")
            logger.info("=" * 50)
            httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("\nServer stopped by user")
    except OSError as e:
        logger.error(f"Server startup error on port {port}: {e}")

"""Conversation context persistence."""

import os
import logging
from datetime import datetime

from src.settings import settings

logger = logging.getLogger(__name__)


def append_context(user_text, assistant_text):
    """Append the user and assistant messages to the context file.

    If the file's last modification time is older than 60 seconds, clear it first.
    """
    try:
        context_path = settings.context_path

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

        os.makedirs(os.path.dirname(context_path), exist_ok=True)
        mode = "w" if truncate_file else "a"
        with open(context_path, mode, encoding="utf-8") as f:
            f.write(f"USER: {user_text}\n")
            f.write(f"GLADOS: {assistant_text}\n")
    except OSError as e:
        logger.error(f"Failed to write to {context_path}: {str(e)}")

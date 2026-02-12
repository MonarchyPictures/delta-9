import logging
import json
import time
from typing import Any, Dict, Optional

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name

    def _format(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        data = {
            "timestamp": time.time(),
            "logger": self.name,
            "message": message,
            "context": context or {}
        }
        return json.dumps(data)

    def info(self, message: str, **kwargs):
        self.logger.info(self._format(message, kwargs))

    def error(self, message: str, **kwargs):
        self.logger.error(self._format(message, kwargs))

    def warning(self, message: str, **kwargs):
        self.logger.warning(self._format(message, kwargs))

    def debug(self, message: str, **kwargs):
        self.logger.debug(self._format(message, kwargs))

def get_logger(name: str):
    return StructuredLogger(name)

from __future__ import annotations
import re
import uuid
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Iterable, List
from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException

log = CustomLogger().get_logger(__name__)
SUPPORTED_EXTENSIONS = {".pdf",".docx",".txt"}

def generate_session_id(prefix:str = "session")-> str:
    est = ZoneInfo("America/New_York")
    return f"{prefix}_{datetime.now(est).strftime('%m%d%Y_%H%M%S')}_{uuid.uuid4().hex[:8]}"


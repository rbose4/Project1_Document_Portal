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

#------- Helper functions for file I/O and loading -----------

def generate_session_id(prefix:str = "session")-> str:
    """Generate a semi-human-readable unique session identifier.

    The ID includes an optional prefix, the current time in the
    America/New_York timezone formatted as `MMDDYYYY_HHMMSS`, and an 8
    character hex suffix from a UUID for collision resistance.

    Args:
        prefix (str): Optional text prefix for the ID. Defaults to "session".

    Returns:
        str: A string like "session_03112026_142530_ab12cd34".
    """
    est = ZoneInfo("America/New_York")
    return f"{prefix}_{datetime.now(est).strftime('%m%d%Y_%H%M%S')}_{uuid.uuid4().hex[:8]}"

def save_uploaded_files(uploaded_files:Iterable, target_dir:Path):
    """Persist uploaded file-like objects to `target_dir`.

    This function will:
    - Ensure `target_dir` exists.
    - Iterate over `uploaded_files` and write supported files
      (by extension) to disk using a cleaned, collision-resistant
      filename.

    Notes:
        Only files with extensions in `SUPPORTED_EXTENSIONS` are saved.
        Each saved filename is the cleaned original stem plus a short
        UUID-derived suffix to avoid collisions.

    Args:
        uploaded_files (Iterable): An iterable of file-like objects.
            Each object is expected to expose either a `read()` method
            or a `getbuffer()` method and may have a `name` attribute.
        target_dir (Path): Path where files should be written.

    Returns:
        List[Path]: Paths of the saved files (in the same order written).

    Raises:
        DocumentPortalException: If any I/O error occurs while saving.
    """
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        saved:List[Path] = []
        for uf in uploaded_files:
            name = getattr(uf,"name","file")
            ext = Path(name).suffix.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                log.warning("Unsupported file skipped", filename = name)
                continue
            # clean file name (only alphanum, dash, underscore)
            safe_name = re.sub(r'[^a-zA-Z0-9_\-]+','_',Path(name).stem).lower().strip('_')
            fname = f"{safe_name}_{uuid.uuid4().hex[:6]}{ext}"
            out = target_dir/fname
            with open(out,"wb") as f:
                if hasattr(uf,"read"):
                    f.write(uf.read())
                else:
                    f.write(uf.getbuffer()) # for fallback
            saved.append(out)
            log.info("File saved for ingestion", uploaded_file=name,saved_as=str(out))
            return saved
    except Exception as e:
        log.error("Failed to save uploaded files", error=str(e), directory=str(target_dir))
        raise DocumentPortalException("Failed to save uploaded files", e) from e


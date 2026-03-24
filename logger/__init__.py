from .custom_logger import CustomLogger
# Create single shared logger instance
GLOBAL_LOGGER = CustomLogger().get_logger("document_portal")
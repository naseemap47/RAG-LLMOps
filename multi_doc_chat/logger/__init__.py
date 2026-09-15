from .logger import Logger as _Logger  # backward compat
try:
    from .logger import Logger
except Exception:
    Logger = _Logger

# Expose a global structlog-style logger used across the codebase
GLOBAL_LOGGER = Logger().get_logger(__name__)
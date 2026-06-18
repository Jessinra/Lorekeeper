import logging
import logging.handlers
import sys
from pathlib import Path

import structlog

_LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s %(message)s"
_MAX_BYTES = 10 * 1024 * 1024  # 10 MB per file
_BACKUP_COUNT = 5
_configured = False


def configure_logging(level: str = "INFO", log_dir: Path | None = None) -> None:
    global _configured
    if _configured:
        return
    _configured = True
    log_level = getattr(logging, level.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(log_level)

    # stderr handler (MCP protocol owns stdout, so we write diagnostics to stderr)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(log_level)
    stderr_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.addHandler(stderr_handler)

    # File handlers — only when a log_dir is provided
    if log_dir is not None:
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        # info.log: INFO and above
        info_handler = logging.handlers.RotatingFileHandler(
            log_dir / "info.log",
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        info_handler.setLevel(logging.INFO)
        info_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        root.addHandler(info_handler)

        # error.log: ERROR and above only
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / "error.log",
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(_LOG_FORMAT))
        root.addHandler(error_handler)

    # Silence noisy third-party loggers
    for name in ("sentence_transformers", "httpx", "httpcore"):
        logging.getLogger(name).setLevel(logging.ERROR)

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

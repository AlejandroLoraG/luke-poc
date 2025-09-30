"""
Shared logging configuration for all services.

This module provides standardized logging setup with structured
formatting for consistent log output across the entire system.
"""

import logging
import sys
from typing import Dict, Any, Optional
from datetime import datetime
import json


class StructuredFormatter(logging.Formatter):
    """
    Custom formatter that outputs structured JSON logs for better
    observability and log aggregation.
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        # Basic log data
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add service information if available
        if hasattr(record, 'service'):
            log_data['service'] = record.service

        # Add extra fields from the log record
        if hasattr(record, '__dict__'):
            extra_fields = {
                key: value for key, value in record.__dict__.items()
                if key not in {
                    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
                    'filename', 'module', 'lineno', 'funcName', 'created',
                    'msecs', 'relativeCreated', 'thread', 'threadName',
                    'processName', 'process', 'getMessage', 'stack_info',
                    'exc_info', 'exc_text'
                }
            }
            if extra_fields:
                log_data['extra'] = extra_fields

        # Add exception information if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': self.formatException(record.exc_info) if record.exc_info else None
            }

        return json.dumps(log_data, default=str, ensure_ascii=False)


class ServiceLoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that automatically adds service context to all log records.
    """

    def __init__(self, logger: logging.Logger, service_name: str):
        """
        Initialize the adapter with service context.

        Args:
            logger: The base logger
            service_name: Name of the service (e.g., 'ai-agent', 'mcp-server')
        """
        super().__init__(logger, {'service': service_name})

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
        """Add service context to log records."""
        extra = kwargs.get('extra', {})
        extra.update(self.extra)
        kwargs['extra'] = extra
        return msg, kwargs


def setup_logging(
    service_name: str,
    log_level: str = "INFO",
    use_json_format: bool = True,
    enable_console: bool = True
) -> ServiceLoggerAdapter:
    """
    Set up standardized logging for a service.

    Args:
        service_name: Name of the service (e.g., 'ai-agent', 'mcp-server')
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json_format: Whether to use structured JSON formatting
        enable_console: Whether to enable console output

    Returns:
        ServiceLoggerAdapter configured for the service
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Get the root logger for this service
    logger = logging.getLogger(service_name)
    logger.setLevel(numeric_level)

    # Clear any existing handlers
    logger.handlers.clear()

    if enable_console:
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)

        if use_json_format:
            # Use structured JSON formatter
            formatter = StructuredFormatter()
        else:
            # Use simple text formatter for development
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )

        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    # Create service-specific logger adapter
    service_logger = ServiceLoggerAdapter(logger, service_name)

    # Log the logger setup
    service_logger.info(
        f"Logging initialized for {service_name}",
        extra={
            "log_level": log_level,
            "json_format": use_json_format,
            "console_enabled": enable_console
        }
    )

    return service_logger


def get_request_logger(
    service_logger: ServiceLoggerAdapter,
    request_id: str,
    operation: Optional[str] = None
) -> logging.LoggerAdapter:
    """
    Create a request-specific logger that includes request context.

    Args:
        service_logger: The base service logger
        request_id: Unique request identifier
        operation: Description of the operation being performed

    Returns:
        Logger adapter with request context
    """
    extra_context = {'request_id': request_id}
    if operation:
        extra_context['operation'] = operation

    class RequestLoggerAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            extra = kwargs.get('extra', {})
            extra.update(extra_context)
            kwargs['extra'] = extra
            return msg, kwargs

    return RequestLoggerAdapter(service_logger.logger, {})


# Correlation ID for tracing requests across services
def generate_correlation_id() -> str:
    """Generate a unique correlation ID for request tracing."""
    import uuid
    return str(uuid.uuid4())


# Common log messages and patterns
class LogMessages:
    """Common log messages for consistency across services."""

    SERVICE_STARTING = "Service starting up"
    SERVICE_READY = "Service ready to accept requests"
    SERVICE_STOPPING = "Service shutting down"

    REQUEST_STARTED = "Request started"
    REQUEST_COMPLETED = "Request completed successfully"
    REQUEST_FAILED = "Request failed"

    EXTERNAL_SERVICE_CALL = "Calling external service"
    EXTERNAL_SERVICE_SUCCESS = "External service call successful"
    EXTERNAL_SERVICE_FAILED = "External service call failed"

    HEALTH_CHECK_PASSED = "Health check passed"
    HEALTH_CHECK_FAILED = "Health check failed"
"""
Structured Logging Configuration for Flight Delay Predictor
Provides consistent logging with context and metrics
"""
import logging
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import contextmanager
import time


class StructuredFormatter(logging.Formatter):
    """
    Formatter that outputs structured JSON logs
    """

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add any extra fields from the record
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)

        return json.dumps(log_data)


class ContextLogger:
    """
    Logger with context management for tracking request flow
    """

    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.context = {}

    def set_context(self, **kwargs):
        """Set context variables for all subsequent logs"""
        self.context.update(kwargs)

    def clear_context(self):
        """Clear all context variables"""
        self.context.clear()

    def _log(self, level: int, message: str, **kwargs):
        """Internal log method that adds context"""
        extra_data = {**self.context, **kwargs}
        extra = {'extra_data': extra_data}
        self.logger.log(level, message, extra=extra)

    def debug(self, message: str, **kwargs):
        """Log debug message with context"""
        self._log(logging.DEBUG, message, **kwargs)

    def info(self, message: str, **kwargs):
        """Log info message with context"""
        self._log(logging.INFO, message, **kwargs)

    def warning(self, message: str, **kwargs):
        """Log warning message with context"""
        self._log(logging.WARNING, message, **kwargs)

    def error(self, message: str, **kwargs):
        """Log error message with context"""
        self._log(logging.ERROR, message, **kwargs)

    def exception(self, message: str, **kwargs):
        """Log exception with context"""
        extra_data = {**self.context, **kwargs}
        extra = {'extra_data': extra_data}
        self.logger.exception(message, extra=extra)

    @contextmanager
    def operation_context(self, operation: str, **kwargs):
        """
        Context manager for tracking operation duration and status

        Usage:
            with logger.operation_context('prediction', flight_number='AA123'):
                # do work
                pass
        """
        start_time = time.time()
        operation_id = f"{operation}_{int(start_time * 1000)}"

        # Add operation context
        old_context = self.context.copy()
        self.context.update({
            'operation': operation,
            'operation_id': operation_id,
            **kwargs
        })

        self.info(f"Starting {operation}", **kwargs)

        try:
            yield
            duration = time.time() - start_time
            self.info(
                f"Completed {operation}",
                duration_seconds=duration,
                status='success',
                **kwargs
            )
        except Exception as e:
            duration = time.time() - start_time
            self.error(
                f"Failed {operation}",
                duration_seconds=duration,
                status='error',
                error=str(e),
                **kwargs
            )
            raise
        finally:
            # Restore old context
            self.context = old_context


def setup_logging(log_level: str = 'INFO', use_json: bool = True):
    """
    Setup logging configuration

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        use_json: Whether to use structured JSON logging
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Remove existing handlers
    root_logger.handlers.clear()

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    if use_json:
        formatter = StructuredFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Silence noisy libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


def get_logger(name: str) -> ContextLogger:
    """Get a context-aware logger instance"""
    return ContextLogger(name)


# Metrics tracking
class MetricsCollector:
    """
    Simple in-memory metrics collector
    """

    def __init__(self):
        self.metrics = {
            'predictions_total': 0,
            'predictions_success': 0,
            'predictions_failed': 0,
            'predictions_using_mock': 0,
            'predictions_using_model': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_duration_seconds': 0.0
        }
        self.logger = get_logger('metrics')

    def increment(self, metric_name: str, value: float = 1.0):
        """Increment a metric counter"""
        if metric_name in self.metrics:
            self.metrics[metric_name] += value
        else:
            self.metrics[metric_name] = value

    def record_prediction(self, duration: float, using_mock: bool, success: bool):
        """Record a prediction event"""
        self.increment('predictions_total')
        self.increment('total_duration_seconds', duration)

        if success:
            self.increment('predictions_success')
        else:
            self.increment('predictions_failed')

        if using_mock:
            self.increment('predictions_using_mock')
        else:
            self.increment('predictions_using_model')

        self.logger.info(
            'Prediction recorded',
            duration_seconds=duration,
            using_mock=using_mock,
            success=success
        )

    def record_cache_hit(self):
        """Record a cache hit"""
        self.increment('cache_hits')

    def record_cache_miss(self):
        """Record a cache miss"""
        self.increment('cache_misses')

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        metrics = self.metrics.copy()

        # Calculate derived metrics
        if metrics['predictions_total'] > 0:
            metrics['avg_duration_seconds'] = (
                metrics['total_duration_seconds'] / metrics['predictions_total']
            )
            metrics['success_rate'] = (
                metrics['predictions_success'] / metrics['predictions_total']
            )
            metrics['mock_usage_rate'] = (
                metrics['predictions_using_mock'] / metrics['predictions_total']
            )

        if (metrics['cache_hits'] + metrics['cache_misses']) > 0:
            metrics['cache_hit_rate'] = (
                metrics['cache_hits'] / (metrics['cache_hits'] + metrics['cache_misses'])
            )

        return metrics

    def reset(self):
        """Reset all metrics"""
        for key in self.metrics:
            self.metrics[key] = 0


# Global metrics collector
_metrics_collector = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector"""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector

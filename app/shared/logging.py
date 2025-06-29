"""
Shared logging configuration for Gaia Platform services.
Extends LLM Platform logging with microservices-specific features.
"""
import logging
import sys
import os
from typing import Optional
from app.shared.config import settings

# ANSI color codes (from LLM Platform)
COLORS = {
    'RED': '\033[91m',
    'MAGENTA': '\033[95m',
    'CYAN': '\033[96m',
    'GREEN': '\033[92m',
    'YELLOW': '\033[93m',
    'BLUE': '\033[94m',
    'ORANGE': '\033[38;5;208m',  # New color for service logs
    'PURPLE': '\033[35m',        # New color for NATS logs
    'RESET': '\033[0m'
}

# Custom log levels (from LLM Platform + new ones)
NETWORK = 25
INPUT = 15
LLM = 35
LIFECYCLE = 45
SERVICE = 22  # New level for inter-service communication
NATS = 18     # New level for NATS messaging

# Add custom levels to logging
logging.addLevelName(NETWORK, 'NETWORK')
logging.addLevelName(INPUT, 'INPUT')
logging.addLevelName(LLM, 'LLM')
logging.addLevelName(LIFECYCLE, 'LIFECYCLE')
logging.addLevelName(SERVICE, 'SERVICE')
logging.addLevelName(NATS, 'NATS')

class GaiaColorFormatter(logging.Formatter):
    """Custom formatter adding color support to log records for Gaia Platform."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with appropriate color based on level."""
        color = COLORS['RESET']
        
        if record.levelno == logging.CRITICAL:
            color = COLORS['RED']
        elif record.levelno == logging.ERROR:
            color = COLORS['MAGENTA']
        elif record.levelno == NETWORK:
            color = COLORS['CYAN']
        elif record.levelno == LIFECYCLE:
            color = COLORS['GREEN']
        elif record.levelno == INPUT:
            color = COLORS['YELLOW']
        elif record.levelno == LLM:
            color = COLORS['BLUE']
        elif record.levelno == SERVICE:
            color = COLORS['ORANGE']
        elif record.levelno == NATS:
            color = COLORS['PURPLE']
            
        record.msg = f"{color}{record.msg}{COLORS['RESET']}"
        return super().format(record)

class GaiaLogger(logging.Logger):
    """Custom logger supporting Gaia Platform's specific log types."""
    
    def network(self, msg: str, *args, **kwargs) -> None:
        """Log network-related events in cyan."""
        self.log(NETWORK, msg, *args, **kwargs)
    
    def input(self, msg: str, *args, **kwargs) -> None:
        """Log user input events in yellow."""
        self.log(INPUT, msg, *args, **kwargs)
    
    def llm(self, msg: str, *args, **kwargs) -> None:
        """Log LLM-related events in blue."""
        self.log(LLM, msg, *args, **kwargs)
    
    def lifecycle(self, msg: str, *args, **kwargs) -> None:
        """Log application lifecycle events in green."""
        self.log(LIFECYCLE, msg, *args, **kwargs)
    
    def service(self, msg: str, *args, **kwargs) -> None:
        """Log inter-service communication events in orange."""
        self.log(SERVICE, msg, *args, **kwargs)
    
    def nats(self, msg: str, *args, **kwargs) -> None:
        """Log NATS messaging events in purple."""
        self.log(NATS, msg, *args, **kwargs)

def setup_service_logger(
    service_name: str, 
    level: Optional[int] = None
) -> GaiaLogger:
    """
    Configure and return a logger instance for a specific Gaia service.
    
    Args:
        service_name: The name of the service (auth, asset, chat, gateway)
        level: Optional logging level (defaults to settings.LOG_LEVEL)
        
    Returns:
        Configured GaiaLogger instance
    """
    # Register custom logger class
    logging.setLoggerClass(GaiaLogger)
    
    # Create logger instance with service-specific name
    logger_name = f"gaia.{service_name}"
    logger = logging.getLogger(logger_name)
    
    if level is not None:
        logger.setLevel(level)
    else:
        # Use log level from settings
        log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
        logger.setLevel(log_level)
    
    # Create console handler with color formatter
    console_handler = logging.StreamHandler(sys.stdout)
    formatter = GaiaColorFormatter(
        fmt=f'%(asctime)s - {service_name} - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(formatter)
    
    # Add handler if not already present
    if not logger.handlers:
        logger.addHandler(console_handler)
    
    return logger

def get_logger(service_name: str = "gaia") -> GaiaLogger:
    """Get or create a logger for the specified service."""
    return setup_service_logger(service_name)

# Default logger for shared modules
logger = get_logger("shared")

def configure_logging_for_service(service_name: str) -> GaiaLogger:
    """
    Configure logging for a specific service with proper formatting.
    This should be called at the start of each service's main module.
    """
    service_logger = setup_service_logger(service_name)
    
    # Set the service name in environment for other modules to use
    os.environ['GAIA_SERVICE_NAME'] = service_name
    
    service_logger.lifecycle(f"Logging configured for {service_name} service")
    service_logger.info(f"Log level set to {settings.LOG_LEVEL}")
    
    return service_logger

def log_service_startup(service_name: str, version: str, port: int) -> None:
    """Log standardized service startup information."""
    service_logger = get_logger(service_name)
    service_logger.lifecycle(f"Starting {service_name} service v{version}")
    service_logger.network(f"Service listening on port {port}")
    service_logger.info(f"Environment: {settings.ENVIRONMENT}")
    if settings.DEBUG:
        service_logger.warning("Debug mode is enabled")

def log_service_shutdown(service_name: str) -> None:
    """Log standardized service shutdown information."""
    service_logger = get_logger(service_name)
    service_logger.lifecycle(f"Shutting down {service_name} service")

def log_nats_event(service_name: str, event_type: str, subject: str, details: str = "") -> None:
    """Log NATS messaging events in a standardized format."""
    service_logger = get_logger(service_name)
    message = f"NATS {event_type}: {subject}"
    if details:
        message += f" - {details}"
    service_logger.nats(message)

def log_service_request(service_name: str, target_service: str, endpoint: str, method: str = "POST") -> None:
    """Log inter-service requests in a standardized format."""
    service_logger = get_logger(service_name)
    service_logger.service(f"{method} {target_service}/{endpoint}")

def log_auth_event(service_name: str, auth_type: str, user_id: str = None, success: bool = True) -> None:
    """Log authentication events in a standardized format."""
    service_logger = get_logger(service_name)
    status = "SUCCESS" if success else "FAILED"
    message = f"Auth {status}: {auth_type}"
    if user_id:
        message += f" (user: {user_id})"
    
    if success:
        service_logger.info(message)
    else:
        service_logger.warning(message)

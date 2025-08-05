"""
Log management utilities for test suite.

Provides centralized log directory management and cleanup.
"""
import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta
import pytest


class TestLogManager:
    """Manages test log files and directories"""
    
    def __init__(self, base_dir: str = None):
        if base_dir is None:
            base_dir = os.getenv("TEST_LOG_DIR", "logs/tests")
        self.base_dir = Path(base_dir)
        self.ensure_log_directory()
    
    def ensure_log_directory(self):
        """Ensure log directory structure exists"""
        # Create main directories
        (self.base_dir / "pytest").mkdir(parents=True, exist_ok=True)
        (self.base_dir / "docker").mkdir(parents=True, exist_ok=True)
        (self.base_dir / "services").mkdir(parents=True, exist_ok=True)
        (self.base_dir / "performance").mkdir(parents=True, exist_ok=True)
    
    def get_log_path(self, log_type: str, name: str = None) -> Path:
        """Get path for a specific log type"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        
        if log_type == "pytest":
            filename = f"test-run-{timestamp}.log" if not name else f"{name}-{timestamp}.log"
            return self.base_dir / "pytest" / filename
        elif log_type == "docker":
            filename = f"docker-build-{timestamp}.log" if not name else f"{name}-{timestamp}.log"
            return self.base_dir / "docker" / filename
        elif log_type == "service":
            filename = f"service-{name}-{timestamp}.log"
            return self.base_dir / "services" / filename
        elif log_type == "performance":
            filename = f"perf-{name}-{timestamp}.log"
            return self.base_dir / "performance" / filename
        else:
            return self.base_dir / f"{log_type}-{timestamp}.log"
    
    def cleanup_old_logs(self, days: int = 7):
        """Remove logs older than specified days"""
        cutoff_time = datetime.now() - timedelta(days=days)
        
        for log_dir in self.base_dir.iterdir():
            if log_dir.is_dir():
                for log_file in log_dir.glob("*.log"):
                    if log_file.stat().st_mtime < cutoff_time.timestamp():
                        try:
                            log_file.unlink()
                        except Exception as e:
                            print(f"Warning: Failed to delete old log {log_file}: {e}")
    
    def get_latest_log(self, log_type: str) -> Path:
        """Get the most recent log file of a specific type"""
        log_dir = self.base_dir / log_type
        if not log_dir.exists():
            return None
        
        log_files = list(log_dir.glob("*.log"))
        if not log_files:
            return None
        
        return max(log_files, key=lambda p: p.stat().st_mtime)
    
    def archive_logs(self, archive_name: str = None):
        """Archive current logs to a zip file"""
        import zipfile
        
        if archive_name is None:
            archive_name = f"test-logs-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        archive_path = self.base_dir.parent / f"{archive_name}.zip"
        
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
            for log_file in self.base_dir.rglob("*.log"):
                arcname = log_file.relative_to(self.base_dir.parent)
                zf.write(log_file, arcname)
        
        return archive_path


# Pytest fixtures
@pytest.fixture(scope="session")
def test_log_manager():
    """Session-scoped log manager"""
    manager = TestLogManager()
    yield manager
    # Optionally cleanup old logs after test session
    if os.getenv("CLEANUP_OLD_LOGS", "false").lower() == "true":
        manager.cleanup_old_logs(days=7)


@pytest.fixture
def log_path(test_log_manager, request):
    """Get a log path for the current test"""
    test_name = request.node.name.replace("/", "_").replace("::", "_")
    return test_log_manager.get_log_path("pytest", test_name)


# Utility functions
def get_test_log_dir():
    """Get the test log directory"""
    return os.getenv("TEST_LOG_DIR", "logs/tests")


def setup_logging_for_test(test_name: str = None):
    """Setup logging configuration for a test"""
    import logging
    from logging.handlers import RotatingFileHandler
    
    log_manager = TestLogManager()
    log_path = log_manager.get_log_path("pytest", test_name)
    
    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Add file handler
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.INFO)
    
    # Add formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    # Also log to console in debug mode
    if os.getenv("DEBUG", "false").lower() == "true":
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger
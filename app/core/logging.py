"""
Core Logging — Loguru Setup
"""
import sys
from loguru import logger


def setup_logging():
    logger.remove()
    logger.add(
        sys.stdout,
        colorize=True,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}</cyan> — <white>{message}</white>",
        level="INFO",
    )
    logger.add(
        "logs/app.log",
        rotation="10 MB",
        retention="30 days",
        level="DEBUG",
        format="{time} | {level} | {name} — {message}",
    )
    return logger

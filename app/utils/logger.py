"""Configuration du logging pour l'application."""

import logging
import os
from datetime import datetime
from pathlib import Path


def setup_logger(name: str = "whatsapp_assistant", log_dir: str = "logs") -> logging.Logger:
    """Configure et retourne un logger avec sortie console et fichier."""
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # Format commun
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler fichier (rotation journalière via nom)
    today = datetime.now().strftime("%Y-%m-%d")
    file_handler = logging.FileHandler(
        log_path / f"assistant_{today}.log", encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    # Handler console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(fmt)
    logger.addHandler(console_handler)

    return logger


# Logger global de l'application
app_logger = setup_logger()

# pylint: disable=logging-fstring-interpolation
import sys
from pathlib import Path
import logging
from typing import Union


def to_path(path: Union[str, Path]) -> Path:
    """ Convert a string to a path, if it is String. """
    if isinstance(path, Path):
        return path
    return Path(path)


def get_logger(path: Path = Path("."), name: str = "gmx_sim.log") -> logging.Logger:
    """It is a LOGGER!"""
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)-8s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    if (log_path := path.resolve() / name).exists():
        mode = "a"
    else:
        mode = "w"
    handler = logging.FileHandler(log_path, mode=mode)
    handler.setFormatter(formatter)
    screen_handler = logging.StreamHandler(stream=sys.stdout)
    screen_handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.addHandler(screen_handler)
    return logger


class FileCreationLogger:
    """ Context manager to log files created during execution."""
    def __init__(self):
        self.files_present = [f.name for f in Path(".").resolve().glob("*")]

    def __enter__(self):
        return self

    def __exit__(self, _exc_type, _exc_val, _exc_tb):
        current_files = [f.name for f in Path(".").resolve().glob("*")]
        new_files = [f for f in current_files if f not in self.files_present]
        logging.info(f"Files created during execution: {new_files}")

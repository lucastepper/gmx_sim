import sys
from pathlib import Path
from .gmx_subprocess import set_env, get_env, run_subprocess
from .utils import get_logger
from .version import __version__

GMXENV = None
LOGGER = get_logger()

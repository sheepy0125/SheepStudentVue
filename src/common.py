"""
StudentVue Data Viewer Common Files
Created by sheepy0125
16/11/2021
"""

### Global imports ###
from pathlib import Path
from tools import Logger

### Constants ###
ROOT_PATH = Path(__file__).parent.parent
DEFAULT_CONFIG_PATH = Path(ROOT_PATH / "config.jsonc")
VERSIONING_PATH = Path(ROOT_PATH / "versioning")
Logger.log(f"Current working directory: {ROOT_PATH}")

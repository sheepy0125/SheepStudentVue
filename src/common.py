"""
StudentVue Data Viewer Common Files
Licensed under the Unlicense (P.D.)
2021-11-16
"""

### Global imports ###
from pathlib import Path
from tools import Logger

### Constants ###
ROOT_PATH = Path(__file__).parent.parent
DEFAULT_CONFIG_PATH = Path(ROOT_PATH / "config.jsonc")
VERSIONING_PATH = Path(ROOT_PATH / "versioning")
Logger.log(f"Current working directory: {ROOT_PATH}")
VERSIONS_FILENAME = "VERSIONS.json"
HASH_FILENAME = "HASH.txt"

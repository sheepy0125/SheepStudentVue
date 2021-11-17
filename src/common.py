"""
StudentVue Data Serializer Common Files
Created by sheepy0125
16/11/2021
"""

### Global imports ###
from pathlib import Path
from config_parser import parse

### Constants ###
ROOT_PATH = Path(__file__).parent.parent
DEFAULT_CONFIG_PATH = Path(ROOT_PATH / "config.jsonc")
CONFIG = parse()

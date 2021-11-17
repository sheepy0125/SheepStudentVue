"""
StudentVue Data Viewer Config Parser
Created by sheepy0125
16/11/2021
"""

from jsonc_parser.parser import JsoncParser
from jsonc_parser.errors import FileError, ParserError
from common import DEFAULT_CONFIG_PATH, Path, Logger

### Parse ###
def parse(config_path: Path | str | None = None) -> dict:
    """
    Parse config, return a dictionary
    If config_path is None, use default config path
    """

    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    try:
        with open(config_path, "r") as config_file:
            config: dict = dict(JsoncParser.parse_str(config_file.read()))
    except FileNotFoundError:
        Logger.fatal(f"Config filepath ({config_path}) doesn't exist")
    except ParserError:
        Logger.fatal(f"Config file isn't a valid JSONC file")
    else:
        if check_config(config):
            Logger.log(f"Config file parsed successfully")
            return config

    # The JSON file being invalid, cannot continue
    Logger.fatal("Couldn't load config file (UNRECOVERABLE)")
    exit(1)


### Check ###
def check_config(config: dict) -> bool:
    """Check config, return if valid"""

    # Used for reference later for logging
    error = None

    try:
        assert isinstance(config["username"], str), "Username is not a string"
        assert config["username"] != "", "Username is empty"
        assert config["username"].isdigit(), "Username is not a number"
        assert len(config["username"]) == 9, "Username is not 9 characters long"
        assert isinstance(config["password"], str), "Password is not a string"
        assert isinstance(config["domain"], str), "Domain is not a string"

    except Exception as exc:
        error = exc

    else:
        return True

    Logger.log_error(error)
    return False

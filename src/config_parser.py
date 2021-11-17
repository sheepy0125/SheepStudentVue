"""
StudentVue Data Serializer Config Parser
Created by sheepy0125
16/11/2021
"""

from jsonc_parser.parser import JsoncParser
from jsonc_parser.errors import FileError, ParserError
from common import DEFAULT_CONFIG_PATH, Path
from tools import Logger

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
        Logger.fatal(f"Config filepath ({config_path!s}) doesn't exist")
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

    try:
        assert config["username"] is str, "Username is not a string"
        assert config["username"] != "", "Username is empty"
        assert config["username"].isdigit(), "Username is not a number"
        assert len(config["username"]) == 9, "Username is not 9 characters long"
        assert config["password"] is str, "Password is not a string"
        assert config["domain"] is str, "Domain is not a string"

    except (AssertionError, KeyError) as error:
        pass  # Will handle outside nested try/except

    except Exception as error:
        Logger.fatal(
            "Config file is invalid, but not for the correct reason... what did you do?"
        )

    else:
        return True

    Logger.log_error(error)
    return False

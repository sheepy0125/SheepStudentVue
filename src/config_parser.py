"""
StudentVue Data Viewer Config Parser
Licensed under the Unlicense (P.D.)
2021-11-16
"""

### Setup ###
from sys import exit as sys_exit
from jsonc_parser.parser import JsoncParser
from jsonc_parser.errors import FileError, ParserError
from common import DEFAULT_CONFIG_PATH, Path, Logger

# Cache
ALREADY_PARSED: dict | None = None


### Parse ###
def parse(config_path: Path = None) -> dict:
    """
    Parse config, return a dictionary
    If config_path is None, use default config path
    """

    if ALREADY_PARSED is not None:
        return ALREADY_PARSED

    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    try:
        with open(config_path, "r", encoding="utf-8") as config_file:
            config: dict = dict(JsoncParser.parse_str(config_file.read()))
    except FileNotFoundError:
        Logger.fatal(f"Config filepath ({config_path}) doesn't exist")
    except FileError as err:
        Logger.fatal(f"Could not open {config_path}!")
        Logger.fatal(Logger.log_error(err))
    except ParserError:
        Logger.fatal("Config file isn't a valid JSONC file")
    else:
        if check_config(config):
            return config

    # The JSON file being invalid, cannot continue
    Logger.fatal("Couldn't load config file (UNRECOVERABLE)")
    sys_exit(1)


### Check ###
def check_config(config: dict) -> bool:
    """Check config, return if valid"""

    # Used for reference later for logging
    err: AssertionError | None = None

    try:
        assert isinstance(config.get("domain"), str), "Domain is not a string"
        assert config["domain"][-1] != "/", "Domain cannot end with trailing slash"
        assert (
            "://" not in config["domain"]
        ), "Domain can not have protocol (i.e. `http(s)://`)"
        assert isinstance(
            config.get("master_key"), str
        ), "Encryption master password is not a string"
        assert isinstance(config.get("port"), int), "Port was not an integer"
        assert config["port"] <= 65535, "Port was too high"
    except AssertionError as exc:
        err = exc
    else:
        global ALREADY_PARSED  # pylint:disable=global-statement
        ALREADY_PARSED = config
        return True

    Logger.fatal(Logger.log_error(err))
    return False

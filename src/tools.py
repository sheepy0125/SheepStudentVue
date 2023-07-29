"""
Tools for StudentVue Data Viewer
Licensed under the Unlicense (P.D.)
2021-11-16
"""

### Setup ###
from os import name as os_name, system as os_system  # Platform checking for ANSI colors
from time import strftime
from dataclasses import dataclass


### Logger ###
class Logger:
    """Log messages with ease"""

    colors: dict = {
        "log": "\033[92m",
        "warn": "\033[93m",
        "fatal": "\033[91m",
        "normal": "\033[0m",
    }

    # If the user isn't on POSIX, allow colors
    if os_name != "posix":
        os_system("color")

    @staticmethod
    def time() -> str:
        """Format current time"""
        return f"{strftime('[%b/%d/%y %I:%M:%S %p]')}"

    @staticmethod
    def log(message: str):
        """Log a message in normal colors"""
        print(
            f"{Logger.time()} {Logger.colors['log']}[INFO] {message!s}"
            f"{Logger.colors['normal']}"
        )

    @staticmethod
    def warn(message: str):
        """Warn a message in warn colors"""
        print(
            f"{Logger.time()} {Logger.colors['warn']}[WARN] {message!s}"
            f"{Logger.colors['normal']}"
        )

    @staticmethod
    def fatal(message: str):
        """Error a message in fatal colors"""
        print(
            f"{Logger.time()} {Logger.colors['fatal']}[FAIL] {message!s}"
            f"{Logger.colors['normal']}"
        )

    @staticmethod
    def log_error(error: Exception):
        """Log an error"""
        error_type = type(error).__name__
        error_lines = []
        current_frame = error.__traceback__
        while True:
            try:
                error_lines.append(current_frame.tb_lineno)
                current_frame = current_frame.tb_next
                if current_frame is None:
                    break
            except Exception as _:  # pylint:disable=broad-exception-caught
                break
        del current_frame
        if len(error_lines) == 0:
            error_lines.append("<unknown error lines>")
        try:
            error_file = str(error.__traceback__.tb_next.tb_frame).split("'")[1]
        except Exception as _:  # pylint:disable=broad-exception-caught
            error_file = "<unknown file>"
        return (
            f"{error_type}: {error!s} (lines "
            f"{', '.join(str(error_line) for error_line in reversed(error_lines))} "
            f"in file {error_file})"
        )


### Exceptions ###
class InvalidCredentialsException(Exception):
    """The credentials provided were incorrect"""


class FetchGradesException(Exception):
    """An exception occurred with fetching grades from StudentVue"""


class SerializeGradesException(Exception):
    """An exception occurred with serializing fetched grades from StudentVue"""


class SaveGradesException(Exception):
    """An exception occurred with saving the grades in the versioning store"""


class LoadGradesException(Exception):
    """An exception occurred with loading the grades from the versioning store"""


class VersioningMismatchedCredentialsException(Exception):
    """Mismatched credentials for versioning"""


class VersioningAlreadyInitialized(Exception):
    """Versioning is already initialized"""


### Dataclasses ###
@dataclass
class SourceDirectory:
    name: str
    files: list[str]

"""
Versioning for StudentVue Data Viewer
Created by sheepy0125
24/08/2022
"""

### Setup ###
from common import Logger, VERSIONING_PATH
from json import dumps, loads


### Versioning ###
class Versioning:
    @staticmethod
    def save(username: str, password: str, data: dict):
        # FIXME: what
        last_updated = "2" + __import__("datetime").datetime.isoformat(
            __import__("datetime").datetime.now()
        )
        # Make directory
        (VERSIONING_PATH / username).mkdir(parents=True, exist_ok=True)
        # Write file
        with open(
            VERSIONING_PATH / username / f"{last_updated[1:-1]}.txt",
            mode="x",  # Exclusive create
        ) as save_file:
            save_file.writelines(
                [
                    f"{username}\n",
                    f"{password}\n",
                    f"{dumps(data)}",
                ]
            )

    @staticmethod
    def load(username: str, password: str, date: str) -> dict:
        """Raises PermissionError if the credentials are invalid"""

        with open(VERSIONING_PATH / username / f"{date}.txt", "r") as load_file:
            verify_username, verify_password, text = load_file.readlines()

        # Validate
        if not (verify_username == username and verify_password == password):
            raise PermissionError

        # Convert to dict
        return loads(text)

    @staticmethod
    def list(username: str) -> list[str]:
        """Returns a list of dates"""

        try:
            return [date.stem for date in (VERSIONING_PATH / username).iterdir()]
        except FileNotFoundError:
            return []

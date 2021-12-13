"""
Data Grabber for StudentVue Data Viewer
Created by sheepy0125
16/11/2021
"""

### Setup ###
from common import Logger
from collections import OrderedDict
from studentvue import StudentVue
from serialize import serialize
from json import loads, dumps


class GradebookGrabber:
    def __init__(self, username: str, password: str, domain: str) -> None:
        self.student_vue = StudentVue(username, password, domain)
        self.username = username
        self.password = password

        unserialized_grades = self.grab_info()

        # Assert grades are good (like if it was a bad login or something not actually)
        assert (
            "error" not in unserialized_grades.keys()
        ), f"{unserialized_grades['error']}"

        self.grades = serialize(unserialized_grades)

    def grab_info(self) -> dict:
        info: list[OrderedDict] = None
        info = self.student_vue.get_gradebook()

        # Convert to list of normal dictionaries (currently is OrderedDict)
        info = loads(dumps(info))

        # Assert that the gradebook isn't just an error (LBYL)
        if "RT_ERROR" in info.keys():
            return {
                "error": (
                    "Failed to get grades from StudentVue! "
                    f"Error: {info['RT_ERROR']['@ERROR_MESSAGE']} (UNRECOVERABLE)"
                )
            }

        Logger.log("Got grades from StudentVue")
        return info

"""
StudentVue Data Serializer
Created by sheepy0125
16/11/2021
"""

### Setup ###
from common import DEFAULT_CONFIG_PATH, Path, Logger
from config_parser import parse
from studentvue import StudentVue
from json import loads, dumps
from collections import OrderedDict
from pandas import DataFrame

CONFIG = parse()

# Get StudentVue object
try:
    student_vue = StudentVue(*CONFIG.values())  # This is a bad idea, but it works.
except Exception as error:
    Logger.fatal(
        "Failed to initialize StudentVue!\nThis can be for multiple reasons, "
        "but most likely it's because the credentials aren't right. Please "
        "check your config file and try again.\n\n"
    )
    Logger.log_error(error)

# Get OrderedDicts of gradebook
grades: list[OrderedDict] | None = None
try:
    grades = student_vue.get_gradebook()
except Exception as error:
    Logger.fatal("Failed to get grades from StudentVue!")
    Logger.log_error(error)

# Convert to list of normal dictionaries
grades = loads(dumps(grades), object_pairs_hook=OrderedDict)

Logger.log("Successfully got grades from StudentVue!")

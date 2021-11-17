"""
StudentVue Data Viewer Data Serializer
Created by sheepy0125
16/11/2021
"""

### Setup ###
from common import ROOT_PATH, Logger
from json import load, dump

### Serialize ###
def serialize(data: dict) -> dict:
    """Converts the loads of data to less data"""

    serialized_data: dict | list = {}  # Will be a list at the end

    ### Cut all unneeded data out ###
    serialized_data = data["Gradebook"]["Courses"]["Course"]  # List of courses
    for course_idx, course in enumerate(serialized_data):
        course = {
            "name": course["@Title"],
            "period": course["@Period"],
            "teacher": course["@Staff"],
            "grade": course["Marks"]["Mark"]["@CalculatedScoreString"],
            "assignments": [],
        }
        for assignment in serialized_data[course_idx]["Marks"]["Mark"]["Assignments"][
            "Assignment"
        ]:
            course["assignments"].append(
                {
                    "name": assignment["@Measure"],
                    "assigned_date": assignment["@DropStartDate"],
                    "due_date": assignment["@DropEndDate"],
                    "type": assignment["@Type"],
                    "grade": assignment["@Score"],
                    "points": assignment["@Points"],
                }
            )

        serialized_data[course_idx] = course

    return serialized_data


### Test ###
if __name__ == "__main__":
    # If running by self, assume testing mode!
    try:
        with open(str(ROOT_PATH / "data-output.json"), "r") as data_file:
            data = load(data_file)
    except FileNotFoundError:
        Logger.warn("No data-output.json found, skipping test")
        exit(0)

    try:
        data_serialized = serialize(data)
    except Exception as error:
        Logger.fatal(f"Failed test of serializing data")
        Logger.log_error(error)
        exit(1)

    Logger.log(f"Successfully serialized data")

    # Write it
    with open(str(ROOT_PATH / "data-serialized.json"), "w") as data_file:
        data_file.truncate(0)
        dump(data_serialized, data_file, indent=4)
    Logger.log(f"Wrote data-serialized.json")

"""
StudentVue Data Viewer Data Serializer
Created by sheepy0125
16/11/2021
"""

### Setup ###
from common import Logger
from html import unescape

### Serialize ###
def serialize(data: dict) -> dict:
    """Converts the loads of data to less data"""

    ### Cut all unneeded data out ###
    grades: dict = data["Gradebook"]["Courses"]["Course"]  # List of courses
    for course_idx, course in enumerate(grades):
        course = {
            "name": unescape(remove_course_id(course["@Title"])),
            "period": course["@Period"],
            "teacher": unescape(course["@Staff"]),
            "grade": course["Marks"]["Mark"]["@CalculatedScoreString"],
            "assignments": [],
        }
        for assignment in (
            grades[course_idx]["Marks"]["Mark"]["Assignments"]["Assignment"],
        )[0]:
            course["assignments"].append(
                {
                    "name": unescape(assignment["@Measure"]),
                    "assigned_date": unescape(assignment["@DropStartDate"]),
                    "due_date": unescape(assignment["@DropEndDate"]),
                    "type": unescape(assignment["@Type"]),
                    "grade": unescape(str(assignment["@Score"])),
                    "points": unescape(assignment["@Points"]),
                }
            )

        grades[course_idx] = course

    return {"last_updated": f"{Logger.time()}", "grades": grades}


### Remove course ID ###
def remove_course_id(course: str) -> str:
    """Removes the course ID from the course name"""

    return course.split(" (")[0]  # the course ID will be something like (12345)

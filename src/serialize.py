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

        assignments: dict = grades[course_idx]["Marks"]["Mark"]["Assignments"]
        assignments_assignment = assignments.get("Assignment", None)
        if assignments_assignment is None:
            # No assignments, could be the start of the year or no courses...
            # either way, just don't bother
            grades[course_idx] = course
            continue

        # If it's not already a list, put it in one
        # This happens if there's only one assignment
        # I should also mention that this StudentVue API is stupid
        if not isinstance(assignments_assignment, list):
            assignments_assignment = [assignments_assignment]

        for assignment in assignments_assignment:
            # Not an assignment
            if isinstance(assignment, str):
                continue
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

    print(grades)
    return {"last_updated": f"{Logger.time()}", "grades": grades}


### Remove course ID ###
def remove_course_id(course: str) -> str:
    """Removes the course ID from the course name"""

    return course.split(" (")[0]  # the course ID will be something like (12345)

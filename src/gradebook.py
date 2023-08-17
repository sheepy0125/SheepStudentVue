"""
Gradebook for StudentVue Data Viewer
Licensed under the Unlicense (P.D.)
2021-11-16
"""

### Setup ###
from time import time
from typing import Any, Callable
from dataclasses import dataclass
from collections import OrderedDict
from json import loads, dumps
from html import unescape
from studentvue import StudentVue
from common import Logger
from versioning import Versioning
from tools import FetchGradesException, VersioningAlreadyInitialized

# Constants (decided against config options for these)
SENTINEL_UNKNOWN_STR: str = "UNKNOWN"
SENTINEL_UNKNOWN_INT: int = -100


### Auxiliary functions ###
def _try_cast(into: Callable, data: Any) -> Any | str | int:
    try:
        return into(data)
    except Exception as _:  # pylint:disable=broad-exception-caught
        if into == str:
            return SENTINEL_UNKNOWN_STR
        return SENTINEL_UNKNOWN_INT


def _and(maybe_sentinel: Any, not_sentinel: Callable) -> None | Any:
    if maybe_sentinel in (SENTINEL_UNKNOWN_INT, SENTINEL_UNKNOWN_STR):
        return None
    return not_sentinel(maybe_sentinel)


@dataclass
class Assignment:
    """An assignment for a :class:`Course`"""

    name: str
    assigned_date: str  # mm/dd/yyyy
    due_date: str  # mm/dd/yyyy
    weight: str  # E.g. "Final Exam" (the trailing "*" is stripped)
    grade: str
    points: str  # E.g. "0.39 / 1.0000"


@dataclass
class Course:
    """A course for :class:`GradebookItem`"""

    name: str  # Course name
    grade: int
    teacher: str
    period: int
    assignments: list[Assignment]
    room: str
    weights: dict[str, float]  # E.g. "Final Exam": 0.10 (the trailing "*" is stripped)


@dataclass
class GradebookInformation:
    """Information about a gradebook.

    All sentinel values are "UNKNOWN" or `0` for integers.

    Note for maintainers: Changing the spec here would mean versioned / past
    grades would potentially become invalidated, as the serialized variant is
    stored there.

    Example tree:
    GradebookInformation(
        last_updated=1234,
        courses=[
            Course(
                name="Intro to Sheep Shearing",
                period=1,
                teacher="Sheepster White",
                grade=39,
                assignments=[
                    Assignment(
                        name="Shear labeling worksheet",
                        assigned_date="8/9/2022",
                        due_date="8/9/2022",
                        type="AKS Progress*",
                        grade=39,
                        points="0.39 / 1.0000",
                    )
                ],
            ),
        ],
    )
    """

    last_updated: int  # Unix timestamp (seconds)
    courses: list[Course]


class Gradebook:
    """A gradebook for a student. Contains the username, password, and grades for
    a session.
    """

    def __init__(self, username: str, password: str, domain: str) -> None:
        self.student_vue: StudentVue = StudentVue(username, password, domain)
        self.username: str = username
        self.password: str = password
        self.domain: str = domain

        self.versioning: None | Versioning = None
        self.unserialized_grades: None | dict = None
        self.grades: None | dict = None

    def init_versioning(self):
        """Initialize versioning"""

        if self.versioning is not None:
            self.versioning.mkdir()
            raise VersioningAlreadyInitialized()

        self.versioning: Versioning = Versioning(
            self.username, self.password, self.grades
        )
        self.versioning.mkdir()

    def grab_info(self):
        """Grab information from StudentVue"""

        if self.grades:
            return

        self.unserialized_grades: dict = self._grab_info()
        self.grades: GradebookInformation = self._serialize()

    def save(self) -> None:
        """Save the current grades to a file."""

        self.versioning.path.mkdir(parents=True, exist_ok=True)
        self.versioning.save()

    def _grab_info(self) -> dict:
        """Grab and serialize info from StudentVue"""

        info: list[OrderedDict] = self.student_vue.get_gradebook()

        # Convert to list of normal dictionaries (currently is OrderedDict)
        info = loads(dumps(info))

        # Assert that the gradebook isn't just an error
        if "RT_ERROR" in info:
            raise FetchGradesException(
                "Failed to get grades from StudentVue! "
                f"Error: {info['RT_ERROR']['@ERROR_MESSAGE']} (UNRECOVERABLE)"
            )

        Logger.log("Got grades from StudentVue")
        return info

    def _serialize(self) -> GradebookInformation:
        """Serialize the raw data into :class:`GradebookInformation`"""

        serialized = GradebookInformation(last_updated=int(time()), courses=[])

        def _remove_course_id(course: str) -> str:
            """Removes the course ID from the course name.
            The course ID will be something like "(12345)"
            """

            return course.split(" (")[0]

        courses: dict = self.unserialized_grades["Gradebook"]["Courses"]["Course"]
        for course_idx, course in enumerate(courses):
            grade: str = course["Marks"]["Mark"]["@CalculatedScoreString"]
            assignments: dict = courses[course_idx]["Marks"]["Mark"]

            weights: dict[str, float] = {}
            weights_available: bool = True
            assignments_weights: None | list[dict] = assignments.get(
                "GradeCalculationSummary"
            )
            if assignments_weights is None or assignments_weights == {}:
                weights_available: bool = False
            else:
                assignments_weights: dict = assignments_weights["AssignmentGradeCalc"]
            if weights_available and (
                not isinstance(assignments_weights, list)
                and isinstance(assignments_weights, dict)
            ):
                assignments_weights: list[dict] = [assignments_weights]
            if weights_available:
                for weight in assignments_weights:
                    if weight == {}:
                        continue
                    percent: str = weight["@Weight"].rstrip("%")
                    weights[weight["@Type"].rstrip("*")] = _and(
                        _try_cast(float, percent), lambda p: p / 100
                    )

            course: Course = Course(
                name=unescape(_remove_course_id(course["@Title"])),
                period=course["@Period"],
                teacher=unescape(course["@Staff"]),
                grade=_try_cast(int, grade),
                assignments=[],
                room=unescape(str(course.get("@Room", SENTINEL_UNKNOWN_STR))),
                weights=weights,
            )

            assignments_assignment: None | list[dict] | dict = assignments[
                "Assignments"
            ].get("Assignment", None)
            if assignments_assignment is None:
                # No assignments, could be the start of the year or no courses...
                # either way, just don't bother (empty course)
                serialized.courses.append(course)
                continue

            # If it's not already a list, put it in one. This happens if there's
            # only one assignment. I should also mention that this StudentVue API
            # is stupid.
            if (
                not isinstance(assignments_assignment, list)
                or isinstance(assignments_assignment, dict),
            )[0]:
                assignments_assignment: list[dict] = [assignments_assignment]

            # Add assignment information
            for assignment in assignments_assignment:
                # Not an assignment
                if isinstance(assignment, str):
                    continue
                grade: str = unescape(
                    str(assignment.get("@Score", SENTINEL_UNKNOWN_STR))
                )
                if grade in ("Not Due", "Not Graded"):
                    grade: str = str(SENTINEL_UNKNOWN_STR)
                assignment_information = Assignment(
                    name=unescape(assignment.get("@Measure", SENTINEL_UNKNOWN_STR)),
                    assigned_date=unescape(
                        assignment.get("@DropStartDate", SENTINEL_UNKNOWN_STR)
                    ),
                    due_date=unescape(
                        assignment.get("@DropEndDate", SENTINEL_UNKNOWN_STR)
                    ),
                    weight=unescape(assignment.get("@Type")).rstrip("*"),
                    grade=grade,
                    points=unescape(assignment.get("@Points", SENTINEL_UNKNOWN_STR)),
                )
                course.assignments.append(assignment_information)

            serialized.courses.append(course)

        return serialized

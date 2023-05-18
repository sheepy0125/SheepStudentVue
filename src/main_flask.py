"""
Flask Server for StudentVue Data Viewer
Created by sheepy0125
16/11/2021
"""

### Setup ###
from json import loads
from pathlib import Path
from common import ROOT_PATH, Logger
from flask import Flask, render_template, request
from grab_data import GradebookGrabber
from config_parser import parse
from traceback import format_exc
from os import mkdir, path, walk

from versioning import Versioning

CONFIG = parse()

app = Flask(
    __name__,
    static_folder=str(ROOT_PATH / "static"),
    template_folder=str(ROOT_PATH / "template"),
)

student_gradebooks: dict = {}  # Stores a GradebookGrabber object for each student


### Functions ###
def get_gradebook(username: str, password: str) -> dict:
    """Gets a gradebook for a student (warning: no error handling)"""

    gradebook_object = GradebookGrabber(username, password, CONFIG["domain"])
    student_gradebooks[username] = gradebook_object
    return gradebook_object.grades


### Error handler ###
@app.errorhandler(500)
def error_handler(e: Exception):
    return render_template("error.html", error=format_exc())


### Routes ###
@app.route("/", methods=["GET", "POST"])
def index():
    # No username or password
    if request.method == "GET":
        return render_template("enter-credentials.html")

    username: str = request.form["username"]
    password: str = request.form["password"]

    Logger.log(f"Attempting to load gradebook for {username}:{password}")

    # Get the gradebook content
    gradebook = get_gradebook(username, password)

    if not path.isdir(f"versioning/{username}"):
        mkdir(f"versioning/{username}")
    Versioning.save(username, password, gradebook)

    return render_template(
        "grade_viewer.html",
        content=gradebook,
        username=username,
        password=password,
        past=True,
    )


@app.route("/past", methods=["POST"])
def past_log_viewer():
    username = request.form["username"]
    password = request.form["password"]

    if not path.isdir(f"versioning/{username}"):
        raise RuntimeError("No entry found.")

    _, _, files = next(walk(f"versioning/{username}"))

    # Get the overview grades for all the files
    # Also, check if the password is valid
    # FIXME: Doesn't account for password changes
    courses = []
    entries = []
    for idx, filename in enumerate(files):
        grades = []
        with open(f"versioning/{username}/{filename}", "r") as grade_entry_file:
            lines = grade_entry_file.readlines()
            if lines[1].strip() != password or lines[0].strip() != username:
                raise RuntimeError("No entry found.")
            serialized = loads(lines[2])
        if len(courses) == 0:
            for course in serialized["grades"]:
                courses.append(course["name"])
        for course in serialized["grades"]:
            grades.append(course["grade"])

        # Convert the 'idx' intoto an 'id'
        entry_id = idx + 1
        entries.append({"id": entry_id, "course_grades": grades, "date": filename})

    return render_template(
        "view_logs.html",
        courses=courses,
        entries=entries,
        username=username,
        password=password,
    )


@app.route("/past/<int:entry_id>", methods=["POST"])
def past_log(entry_id: int):
    username = request.form["username"]
    password = request.form["password"]
    # Convert the 'id' into an 'idx'
    entry_id -= 1
    if entry_id < 0:
        raise RuntimeError("ID cannot be negative.")

    user_data_path = Path(f"versioning/{username}")
    if not (
        user_data_path.exists()
        and user_data_path.is_relative_to("versioning")
        and user_data_path != Path("versioning")
    ):
        raise RuntimeError("No entry found.")

    _, _, files = next(walk(f"versioning/{username}/"))

    if len(files) < entry_id:
        raise RuntimeError("No entry found.")

    with open(f"versioning/{username}/{files[entry_id]}", "r") as grade_entry_file:
        lines = grade_entry_file.readlines()
        print(lines)
        if lines[1].strip() != password or lines[0].strip() != username:
            raise RuntimeError("No entry found.")

    serialized = loads(lines[2])

    return render_template(
        "grade_viewer.html",
        content=serialized,
        username=username,
        password=password,
        past=True,
    )


### Run ###
if __name__ == "__main__":
    Logger.log("Running Flask server")
    app.run(port=5000, host="0.0.0.0", debug=False, use_reloader=False)

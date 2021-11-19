"""
Flask Server for StudentVue Data Viewer
Created by sheepy0125
16/11/2021
"""

### Setup ###
from common import ROOT_PATH, Logger
from flask import Flask, render_template, request
from grab_data import GradebookGrabber
from config_parser import parse

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


### Routes ###
@app.route("/", methods=["GET", "POST"])
def index():
    # No username or password
    if request.method == "GET":
        return render_template("enter-credentials.html")

    username: str = request.form["username"]
    password: str = request.form["password"]

    Logger.log(f"Attempting to load gradebook for {username}")

    try:
        # Get the gradebook content
        gradebook = get_gradebook(username, password)
    except Exception as error:
        Logger.log_error(error)

        return render_template(
            "error.html",
            error=(
                f"{type(error).__name__}: {str(error)} "
                + f"(line {error.__traceback__.tb_lineno})"
            ),
        )

    return render_template(
        "grade_viewer.html", content=gradebook, username=username, password=password
    )


### Run ###
if __name__ == "__main__":
    Logger.log("Running Flask server")
    app.run(debug=True)

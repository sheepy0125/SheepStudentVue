"""
Flask Server for StudentVue Data Viewer
Licensed under the Unlicense (P.D.)
2021-11-16
"""

### Setup ###
from traceback import format_exc
from dataclasses import asdict, dataclass
from typing import TypeAlias
from datetime import datetime
from pathlib import Path
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import (
    Flask,
    Response,
    render_template,
    request,
    make_response,
    flash,
    redirect,
    session,
    url_for,
)
from tzlocal import get_localzone
from gradebook import (
    Gradebook,
    GradebookInformation,
    SENTINEL_UNKNOWN_INT,
    SENTINEL_UNKNOWN_STR,
)
from versioning import Versioning, VersioningItem
from tools import VersioningMismatchedCredentialsException
from config_parser import parse
from common import ROOT_PATH, VERSIONING_PATH, HASH_FILENAME, Logger
from tools import (
    InvalidCredentialsException,
    VersioningAlreadyInitialized,
    SourceDirectory,
)

# Constants
CONFIG: dict = parse()
LOGIN_PAGE: str = "enter-credentials.html"
GRADE_VIEWER_PAGE: str = "grade-viewer.html"
PASSWORD_MISMATCH_PAGE: str = "password-mismatch.html"
CONFIRM_VERSION_HISTORY_DELETION_PAGE: str = "confirm-version-history-deletion.html"
MIGRATE_PASSWORD_PAGE: str = "migrate-password.html"
VERSIONING_HISTORY_PAGE: str = "view-versioning-history.html"
ABOUT_PAGE: str = "about.html"
SOURCE_PAGE: str = "source.html"
# ---
INPUT_CREDENTIALS_MESSAGE: str = "Please input your credentials and login."
INVALID_CREDENTIALS_MESSAGE: str = "Invalid credentials."
INVALID_PATH_MESSAGE: str = "Invalid path."
# ---
SOURCE_FILES = [
    SourceDirectory(
        name="",
        files=[
            Path("config.template.jsonc"),
            Path("copying"),
            Path("readme.md"),
            Path("requirements.txt"),
        ],
    ),
    SourceDirectory(
        name="src",
        files=[
            f.relative_to(ROOT_PATH / "src")
            for f in (ROOT_PATH / "src").iterdir()
            if not f.is_dir()
        ],
    ),
    SourceDirectory(
        name="static/css",
        files=[
            f.relative_to(ROOT_PATH / "static" / "css")
            for f in (ROOT_PATH / "static" / "css").iterdir()
            if not f.is_dir()
        ],
    ),
    SourceDirectory(
        name="template",
        files=[
            f.relative_to(ROOT_PATH / "template")
            for f in (ROOT_PATH / "template").iterdir()
            if not f.is_dir()
        ],
    ),
]


### Data structures ###
class DeleteVersionHistoryConfirmationChoice:  # pylint:disable=too-few-public-methods
    """An enum to store the values for the radio buttons for when a user selects
    their confirmation choice to delete their versioning history.
    """

    VARIANT: TypeAlias = int  # Type annotation

    KEEP: VARIANT = 1
    DELETE: VARIANT = 2


class PasswordMismatchChoice:  # pylint:disable=too-few-public-methods
    """A choice that a user with a password mismatch has to resolve the issue"""

    VARIANT: TypeAlias = int  # Type annotation

    UNDECIDED: VARIANT = 0  # Default
    DELETE: VARIANT = 1
    CONTINUE: VARIANT = 2
    MIGRATE: VARIANT = 3


@dataclass
class PasswordMismatchInformation:
    """Information for a user with a password mismatch"""

    old_password: str | None  # Currently stored
    new_password: str  # Works for StudentVue
    choice: PasswordMismatchChoice.VARIANT


### Session data ###
# Keys are usernames.
PASSWORD_MISMATCH_USERS: dict[str, PasswordMismatchInformation] = {}
GRADEBOOKS: dict[str, Gradebook] = {}


@dataclass
class SessionData:
    """Data stored for a user session"""

    username: str
    password: str


### App ###
app = Flask(
    __name__,
    static_folder=str(ROOT_PATH / "static"),
    template_folder=str(ROOT_PATH / "template"),
)
app.secret_key = CONFIG["master_key"]
limiter = Limiter(app)


### Functions ###
def get_gradebook(username: str, password: str) -> Gradebook:
    """Gets a gradebook for a student (no error handling)"""

    # Session gradebook
    if gradebook := GRADEBOOKS.get(username):
        # Synchronize credentials. They may be out of sync if a password mismatch occurs.
        gradebook.password = password
        gradebook.versioning.password = password
        del GRADEBOOKS[username]
        return gradebook

    # Construct a new gradebook
    return Gradebook(username, password, CONFIG["domain"])


def get_credentials() -> tuple[str, str, bool]:
    """Return the username and password respectively from cookies, POST data, or session.
    Also return if both credentials were obtained.
    """

    username: str | None = (
        request.form.get("username"),
        session.get("username"),
        request.cookies.get("username"),
    )
    username: str | None = (
        next((x for x in username if x is not None), None) if any(username) else None
    )
    password: str | None = (
        request.form.get("password"),
        session.get("password"),
        request.cookies.get("password"),
    )
    password: str | None = (
        next((x for x in password if x is not None), None) if any(password) else None
    )

    return username, password, (username is not None and password is not None)


def get_previous_page(default: str = "/?login=true") -> str:
    """Get the previous route out of the session, or the default page"""

    if prev_route := session.get("previous_route", None):
        return prev_route
    return default


def update_previous_page(route: str):
    """Update the previous page with the current route"""

    # Don't include duplicate routes
    if (temp_route := session.get("temp_route")) == route:
        return
    session["previous_route"] = temp_route
    session["temp_route"] = route


### Error handler ###
@app.errorhandler(500)
def error_handler(_: Exception):
    """On an internal server error, this will be plopped"""

    return render_template("error.html", error=format_exc())


### Routes ###
@limiter.limit("1 per second")
@app.route("/", methods=["GET", "POST"])
def index_route():
    """If there are credentials in cookies or POST form data, render the gradebook
    viewer. Otherwise, render the login page.
    """

    username, password, obtained_creds = get_credentials()
    past: bool = request.form.get("past", False)

    session["username"]: str = username
    session["password"]: str = password

    # If the request arguments request to go to the login page, or if we did not
    # obtain any login credentials, ship the user to the login page
    if (len(request.args.get("login", "")) > 0) or not obtained_creds:
        session["redirect"] = request.args.get("redirect", "")
        session.pop("password", None)
        response: Response = make_response(
            render_template(
                LOGIN_PAGE,
                username=username if username is not None else "",
                password=password if password is not None else "",
                domain=CONFIG["domain"],
                past=not session["redirect"],
            )
        )
        response.delete_cookie("password")
        return response

    # Past
    if past:
        session["redirect"] = "past_grades_route"

    # Redirect handler
    if (to_redirect := session.get("redirect")) and len(to_redirect) > 0:
        session.pop("redirect", None)
        return redirect(url_for(to_redirect))

    # Attempt to fetch the gradebook and save it
    # Potentially we can not save the gradebook should the password allow access to the
    # gradebook from StudentVue but it does not match with the hash on record. In such
    # case, show the user a choice. The user could also have been shown a choice and
    # chosen to continue on to StudentVue without saving, in which case we should just
    # disable versioning and show the user their grades. The grades in that case would
    # be cached to prevent hitting StudentVue again.
    gradebook: Gradebook
    is_versioning_available: bool = False
    try:
        gradebook: Gradebook = get_gradebook(username, password)
        gradebook.grab_info()

        # This will fail if the user has had a password mismatch.
        try:
            gradebook.init_versioning()
        except VersioningAlreadyInitialized:
            ...
        gradebook.save()
        is_versioning_available: bool = True
    except InvalidCredentialsException:
        flash(INVALID_CREDENTIALS_MESSAGE)
        return redirect("/clear-cookies")
    except VersioningMismatchedCredentialsException:
        # Has the user already been through this screen but chosen to continue?
        if (
            PASSWORD_MISMATCH_USERS.get(username) is not None
            and PASSWORD_MISMATCH_USERS[username].choice
            == PasswordMismatchChoice.CONTINUE
        ):
            # Allow them to continue to the login page, just without versioning
            is_versioning_available: bool = False
            del PASSWORD_MISMATCH_USERS[username]
        else:
            # Show user some options
            PASSWORD_MISMATCH_USERS[username]: PasswordMismatchChoice = (
                PasswordMismatchInformation(
                    old_password=None,
                    new_password=password,
                    choice=PasswordMismatchChoice.UNDECIDED,
                ),
            )[0]
            GRADEBOOKS[username] = gradebook
            return redirect("/password-mismatch")

    if not is_versioning_available:
        flash("Versioning is currently disabled.")

    response: Response = make_response(
        render_template(
            GRADE_VIEWER_PAGE,
            content=asdict(gradebook.grades),
            past=False,
            is_versioning_available=is_versioning_available,
            SENTINEL_UNKNOWN_INT=SENTINEL_UNKNOWN_INT,
            SENTINEL_UNKNOWN_STR=SENTINEL_UNKNOWN_STR,
        )
    )
    response.set_cookie("username", username)
    response.set_cookie("password", password)
    return response


@limiter.limit("1 per 3 second")
@app.route("/past", methods=["GET", "POST"])
def past_grades_route():
    """View past grades"""

    username, password, obtained_creds = get_credentials()
    update_previous_page("/past")

    if not obtained_creds:
        flash(INPUT_CREDENTIALS_MESSAGE)
        return redirect("/?login=true&redirect=past_grades_route")

    # Get the list of passwords
    versioning: Versioning
    versioning_list: list[VersioningItem]
    try:
        versioning: Versioning = Versioning(
            username=username, password=password, serialized=None
        )
        versioning_list: list[VersioningItem] = versioning.list_history()
    except InvalidCredentialsException:
        flash(INVALID_CREDENTIALS_MESSAGE)
        return redirect("/?login=true")

    # Show versioning list
    if request.method.lower() == "get":
        # A quick function to get the course names
        course_names: callable = lambda list_item: [
            course["name"] for course in list_item["courses"]
        ]
        return render_template(
            VERSIONING_HISTORY_PAGE,
            entries=[
                asdict(versioning_item) for versioning_item in reversed(versioning_list)
            ],
            datetime=datetime,
            local_timezone=get_localzone(),
            SENTINEL_UNKNOWN_INT=SENTINEL_UNKNOWN_INT,
            range=range,
            len=len,
            course_names=course_names,
        )

    # Load version
    timestamp: int
    try:
        timestamp: int = int(request.form["timestamp"])
    except (KeyError, ValueError):
        flash("Invalid timestamp provided.")
        return redirect(get_previous_page())

    past_grades: GradebookInformation
    try:
        past_grades: GradebookInformation = versioning.load(timestamp)
    except InvalidCredentialsException:
        flash(INVALID_CREDENTIALS_MESSAGE)
        return redirect("/?login=true")

    return render_template(
        GRADE_VIEWER_PAGE,
        content=asdict(past_grades),
        past=True,
        is_versioning_available=True,
        SENTINEL_UNKNOWN_INT=SENTINEL_UNKNOWN_INT,
        SENTINEL_UNKNOWN_STR=SENTINEL_UNKNOWN_STR,
    )


@limiter.limit("1 per 3 second")
@app.route("/password-mismatch", methods=["GET", "POST"])
def password_mismatch_route():
    """Fixing the password mismatch"""

    username, password, obtained_creds = get_credentials()
    update_previous_page("/password-mismatch")
    if not obtained_creds:
        flash(INPUT_CREDENTIALS_MESSAGE)
        return redirect("/?login=true&redirect=password_mismatch_route")

    # Validate user
    if username not in PASSWORD_MISMATCH_USERS:
        flash(f"User {username} does not need to update a versioning crypt password.")
        response = make_response(redirect("/clear-cookies"))
        return response

    # Show the options page
    if request.method.lower() == "get":
        return render_template(PASSWORD_MISMATCH_PAGE)

    # Validate password
    if password != PASSWORD_MISMATCH_USERS[username].new_password:
        flash(INVALID_CREDENTIALS_MESSAGE)
        return redirect("/?login=true")

    # Handle choice
    choice_made = int(request.form.get("option", 0))
    PASSWORD_MISMATCH_USERS[username].choice = int(choice_made)
    if choice_made == PasswordMismatchChoice.CONTINUE:
        return redirect("/")
    if choice_made == PasswordMismatchChoice.DELETE:
        return redirect("/delete-versioning-history")
    if choice_made == PasswordMismatchChoice.MIGRATE:
        return redirect("/migrate-password")

    flash("That was not a valid choice.")
    return redirect("/password-mismatch")


@limiter.limit("1 per 3 second")
@app.route("/migrate-password", methods=["GET", "POST"])
def migrate_password_route():
    """Migrate the versioning encryption password for a user"""

    username, old_password, obtained_creds = get_credentials()
    if not obtained_creds:
        flash(INPUT_CREDENTIALS_MESSAGE)
        return redirect("/?login=true&redirect=migrate_password_route")

    # Validate user
    if username not in PASSWORD_MISMATCH_USERS:
        flash(f"User {username} does not need to update a versioning crypt password.")
        response = make_response(redirect("/clear-cookies"))
        return response

    # Show migrate password page
    if request.method.lower() == "get":
        return render_template(MIGRATE_PASSWORD_PAGE)

    # Ensure the old password isn't the new password
    new_password = PASSWORD_MISMATCH_USERS[username].new_password
    if old_password == new_password:
        flash("The new password cannot be the same as the old password")
        return redirect("/migrate-password")

    # Attempt to change the user password
    try:
        GRADEBOOKS[username].versioning.migrate(old_password, new_password)
    except (
        VersioningMismatchedCredentialsException,
        InvalidCredentialsException,
    ):
        flash("Invalid old password.")
        return redirect("/migrate-password")

    return redirect("/")


@limiter.limit("1 per 3 second")
@app.route("/delete-versioning-history", methods=["GET", "POST"])
def delete_versioning_history_route():
    """Delete versioning history for a user"""

    username, password, obtained_creds = get_credentials()
    update_previous_page("/delete-versioning-history")
    if not obtained_creds:
        flash(INPUT_CREDENTIALS_MESSAGE)
        return redirect("/?login=true&redirect=delete_versioning_history_route")

    # Show confirmation page
    if request.method.lower() == "get":
        return render_template(CONFIRM_VERSION_HISTORY_DELETION_PAGE)

    # Handle confirmation choice
    choice = int(request.form.get("option", 0))
    if choice != DeleteVersionHistoryConfirmationChoice.DELETE:
        flash("Canceled deletion.")
        return redirect(get_previous_page())

    # Validate password. If the user is currently trying to fix a version history
    # crypt password mismatch, then we need to use the new password stored there.
    is_password_valid: bool | None = None
    if username in PASSWORD_MISMATCH_USERS:
        is_password_valid: bool = (
            PASSWORD_MISMATCH_USERS[username].new_password == password
        )
    # Otherwise, we just need to compare the password hash.
    if is_password_valid is None:
        try:
            is_password_valid: bool = (
                Versioning.hash_for_user(username)
                == Versioning.hash_generic(username, password, CONFIG["master_key"]),
            )[0]
        except FileNotFoundError:
            ...

    if not is_password_valid:
        flash(f"{INVALID_CREDENTIALS_MESSAGE.strip('.')} or no versioning history.")
        return redirect("/?login=true")

    # Delete data
    Versioning.remove_user_data(username)
    if username in PASSWORD_MISMATCH_USERS:
        del PASSWORD_MISMATCH_USERS[username]
    if username in GRADEBOOKS:
        GRADEBOOKS[username].versioning = None
        GRADEBOOKS[username].init_versioning()
    flash("Version history removed.")

    return redirect(get_previous_page())


@limiter.limit("1 per second")
@app.route("/clear-cookies", methods=["GET"])
def clear_cookies_route():
    """Clear cookies and revert to login"""

    flash("Cleared login cookies.")
    response = make_response(redirect("/?login=true"))
    response.delete_cookie("username")
    response.delete_cookie("password")
    session.clear()

    return response


@limiter.limit("1 per 1 second")
@app.route("/about")
def about_route():
    """Show the user information about this website"""

    update_previous_page("/about")
    return render_template(ABOUT_PAGE)


@limiter.limit("1 per 1 second")
@app.route("/source-list")
def source_route():
    """Show the user the source code tree (not grabbing a file)"""

    update_previous_page("/source")
    return render_template(
        SOURCE_PAGE, files=[asdict(directory) for directory in SOURCE_FILES]
    )


@limiter.limit("1 per 1 second")
@app.route("/source/<path:path>")
def source_file_route(path: str):
    """Return a file from the source code"""

    # Ensure path validity
    path: Path = Path(path)
    if (not path.exists()) or (path <= ROOT_PATH):
        flash(INVALID_PATH_MESSAGE)
        return redirect("/source-list")

    for valid_path in SOURCE_FILES:
        try:
            if path.relative_to(Path(valid_path.name)) in valid_path.files:
                break
        except ValueError as _:  # Paths aren't relative to each other
            continue
    else:
        flash(INVALID_PATH_MESSAGE)
        return redirect("/source-list")

    # Load file
    resp: Response
    with open(path, "r", encoding="utf-8") as source_file:
        resp: Response = Response(
            response=source_file.read(), status=200, content_type="text/plain"
        )
    return resp


### Run ###
if __name__ == "__main__":
    Logger.log("Running Flask server")
    app.run(port=CONFIG["port"], host="0.0.0.0", debug=True, use_reloader=True)

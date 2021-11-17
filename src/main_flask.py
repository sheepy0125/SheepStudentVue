"""
Flask Server for StudentVue Data Viewer
Created by sheepy0125
16/11/2021
"""

### Setup ###
from common import ROOT_PATH, Logger
from flask import Flask, render_template
from json import load

app = Flask(
    __name__,
    static_folder=str(ROOT_PATH / "static"),
    template_folder=str(ROOT_PATH / "template"),
)

### Grab data ###
data: dict = {}
with open(str(ROOT_PATH / "data-serialized.json"), "r") as data_file:
    data = load(data_file)

### Flask ###
@app.route("/")
def index():
    return render_template("index.html", content=data)


### Run ###
if __name__ == "__main__":
    app.run(debug=True)

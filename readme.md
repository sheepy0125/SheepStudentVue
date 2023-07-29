# SheepStudentVue - A grade viewer

A tool I made to view grades from the StudentVue module.

This can do nothing more than view grades, and was only created because the
StudentVue website is exceptionally slow looking between classes.

P.S. the design is horrible and was mostly made in an afternoon

## Usage

First, clone this repository.

Second, make a config file `config.jsonc` in the root directory. See `config.template.jsonc` for instructions.

You also will need Python (and pip) as well as the requirements in
requirements.txt, which can be installed by

```sh
python3 -m pip install -r requirements.txt
```

Now, run the webserver

```sh
python3 src/main_flask.py
```

and go to http://localhost:`PORT`/ (where PORT is set in your `config.jsonc`)

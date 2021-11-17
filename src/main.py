"""
StudentVue Data Viewer
Created by sheepy0125
16/11/2021
"""

### Setup ###
from grab_data import grades
from serialize import serialize

### Run ###
if __name__ == "__main__":
    serialized_data = serialize(grades)
    import main_flask  # Will run the flask server

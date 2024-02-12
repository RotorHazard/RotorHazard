# Helper module to host references to Flask APP and SQLAlchemy database

APP = None
DB = None

def set_objects(app_obj, db_obj):
    global APP
    APP = app_obj
    global DB
    DB = db_obj

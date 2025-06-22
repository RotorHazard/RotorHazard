# Helper module to host reference to Flask APP object

APP = None

def set_flask_app(app_obj):
    global APP
    APP = app_obj

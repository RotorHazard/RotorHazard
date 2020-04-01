#
# Option helpers
#

import Database

GLOBALS_CACHE = {} # Local Python cache for global settings
def primeGlobalsCache():
    global GLOBALS_CACHE

    settings = Database.GlobalSettings.query.all()
    for setting in settings:
        GLOBALS_CACHE[setting.option_name] = setting.option_value

def get(option, default_value=False):
    try:
        val = GLOBALS_CACHE[option]
        if val or val == "":
            return val
        else:
            return default_value
    except:
        return default_value

def set(option, value):
    GLOBALS_CACHE[option] = value

    settings = Database.GlobalSettings.query.filter_by(option_name=option).one_or_none()
    if settings:
        settings.option_value = value
    else:
        Database.DB.session.add(Database.GlobalSettings(option_name=option, option_value=value))
    Database.DB.session.commit()

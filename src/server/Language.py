#
# Translation functions
#
import logging
import json
import Options

logger = logging.getLogger(__name__)

LANGUAGE_FILE_NAME = 'language.json'

Languages = {}

InitResultStr = None
InitResultLogLevel = logging.INFO

# Load language file
try:
    with open(LANGUAGE_FILE_NAME, 'r', encoding="utf8") as f:
        Languages = json.load(f)
    InitResultStr = 'Language file imported'
    InitResultLogLevel = logging.DEBUG
except IOError:
    InitResultStr = 'No language file found, using defaults'
    InitResultLogLevel = logging.WARN
except ValueError:
    InitResultStr = 'Language file invalid, using defaults'
    InitResultLogLevel = logging.ERROR

# Writes a log message describing the result of the module initialization.
def logInitResultMessage():
    if InitResultStr:
        logger.log(InitResultLogLevel, InitResultStr)

def __(text, domain=''):
    # return translated string
    if not domain:
        lang = Options.get('currentLanguage')

    if lang:
        if lang in Languages:
            if text in Languages[lang]['values']:
                return Languages[lang]['values'][text]
    return text

def getLanguages():
    # get list of available languages
    langs = []
    for lang in Languages:
        l = {}
        l['id'] = lang
        l['name'] = Languages[lang]['name']
        langs.append(l)
    return langs

def getAllLanguages():
    # return full language dictionary
    return Languages

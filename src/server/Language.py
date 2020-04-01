#
# Translation functions
#

import Options
import json

LANGUAGE_FILE_NAME = 'language.json'

Languages = {}
# Load language file
try:
    with open(LANGUAGE_FILE_NAME, 'r') as f:
        Languages = json.load(f)
    print 'Language file imported'
except IOError:
    print 'No language file found, using defaults'
except ValueError:
    print 'Language file invalid, using defaults'

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

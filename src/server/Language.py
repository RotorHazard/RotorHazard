#
# Translation functions
#
import logging
import json
import io

logger = logging.getLogger(__name__)

class Language():
    LANGUAGE_FILE_NAME = 'server/language.json'

    Languages = {}

    def __init__(self, RHData):
        self._RHData = RHData

        self._InitResultStr = None
        self._InitResultLogLevel = logging.INFO

        # Load language file
        try:
            with io.open(self.LANGUAGE_FILE_NAME, 'r', encoding="utf8") as f:
                self._Languages = json.load(f)
            self._InitResultStr = 'Language file imported'
            self._InitResultLogLevel = logging.DEBUG
        except IOError:
            self._InitResultStr = 'No language file found, using defaults'
            self._InitResultLogLevel = logging.WARN
        except ValueError:
            self._InitResultStr = 'Language file invalid, using defaults'
            self._InitResultLogLevel = logging.ERROR

    # Writes a log message describing the result of the module initialization.
    def logInitResultMessage(self):
        if self._InitResultStr:
            logger.log(self._InitResultLogLevel, self._InitResultStr)

    def __(self, text, domain=''):
        # return translated string
        if not domain:
            lang = self._RHData.get_option('currentLanguage')

        if lang:
            if lang in self._Languages:
                if text in self._Languages[lang]['values']:
                    return self._Languages[lang]['values'][text]
        return text

    def getLanguages(self):
        # get list of available languages
        langs = []
        for lang in self._Languages:
            l = {}
            l['id'] = lang
            l['name'] = self._Languages[lang]['name']
            langs.append(l)
        return langs

    def getAllLanguages(self):
        # return full language dictionary
        return self._Languages

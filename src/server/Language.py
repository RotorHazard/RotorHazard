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

        # Load language file
        try:
            with io.open(self.LANGUAGE_FILE_NAME, 'r', encoding="utf8") as f:
                self._Languages = json.load(f)
            logger.debug('Language file imported')
        except IOError:
            logger.warn('No language file found, using defaults')
        except ValueError:
            logger.error('Language file invalid, using defaults')

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

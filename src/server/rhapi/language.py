"""View and retrieve loaded translation strings."""

_racecontext = None

@property
def languages():
    """`Read Only` List of available languages.

    :return: list of languages
    :rtype: list[string]
    """
    return _racecontext.language.getLanguages()

@property
def dictionary():
    """`Read Only` Full translation dictionary of all loaded languages.

    :return: Translation dict
    :rtype: dict
    """
    return _racecontext.language.getAllLanguages()

def __(text, domain=''):
    """Translate text.

    :param text: Input to translate
    :type text: str
    :param domain: Language to use, overriding system setting, defaults to ''
    :type domain: str, optional
    :return: Returns translated string, or text if not possible.
    :rtype: str
    """
    return _racecontext.language.__(text, domain)
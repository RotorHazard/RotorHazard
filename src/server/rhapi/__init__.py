"""Access race functions and details"""

import rhapi.ui
import rhapi.fields
import rhapi.db
import rhapi.io
import rhapi.heatgen
import rhapi.classrank
import rhapi.points
import rhapi.led
import rhapi.vrxcontrol
import rhapi.race
import rhapi.language
import rhapi.interface
import rhapi.config
import rhapi.sensors
import rhapi.eventresults
import rhapi.events

API_VERSION_MAJOR = 1
"""API major version"""
API_VERSION_MINOR = 1
"""API minor version"""

server_info = None

def _setup_RHAPI(race_context):
    """Adds race context to the RHAPI modules"""

    rhapi.ui._racecontext               = race_context
    rhapi.fields._racecontext           = race_context
    rhapi.db._racecontext               = race_context
    rhapi.io._racecontext               = race_context
    rhapi.heatgen._racecontext          = race_context
    rhapi.classrank._racecontext        = race_context
    rhapi.points._racecontext           = race_context
    rhapi.led._racecontext              = race_context
    rhapi.vrxcontrol._racecontext       = race_context
    rhapi.race._racecontext             = race_context
    rhapi.language._racecontext         = race_context
    rhapi.interface._racecontext        = race_context
    rhapi.config._racecontext           = race_context
    rhapi.sensors._racecontext          = race_context
    rhapi.eventresults._racecontext     = race_context
    rhapi.events._racecontext           = race_context

class _RHAPI():
    """An object providing backwards compatibility for the RHAPI"""

    server_info = None
    ui = rhapi.ui
    """A handle for an instance of :module:`rhapi.ui`"""
    fields = rhapi.fields
    """A handle for an instance of :module:`rhapi.fields`"""
    db = rhapi.db
    """A handle for an instance of :module:`rhapi.db`"""
    io = rhapi.io
    """A handle for an instance of :module:`rhapi.io`"""
    heatgen = rhapi.heatgen
    """A handle for an instance of :module:`rhapi.heatgen`"""
    classrank = rhapi.classrank
    """A handle for an instance of :module:`rhapi.classrank`"""
    points = rhapi.points
    """A handle for an instance of :module:`rhapi.points`"""
    led = rhapi.led
    """A handle for an instance of :module:`rhapi.led`"""
    vrxcontrol = rhapi.vrxcontrol
    """A handle for an instance of :module:`rhapi.vrxcontrol`"""
    race = rhapi.race
    """A handle for an instance of :module:`rhapi.race`"""
    language = rhapi.language
    """A handle for an instance of :module:`rhapi.language`"""
    interface = rhapi.interface
    """A handle for an instance of :module:`rhapi.interface`"""
    config = rhapi.config
    """A handle for an instance of :module:`rhapi.config`"""
    sensors = rhapi.sensors
    """A handle for an instance of :module:`rhapi.sensors`"""
    eventresults = rhapi.eventresults
    """A handle for an instance of :module:`rhapi.eventresults`"""
    events = rhapi.events
    """A handle for an instance of :module:`rhapi.events`"""
    __ = rhapi.language.__ # shortcut access
    """A shortcut handle for :meth:`rhapi.language.__`"""

    def __init__(self):
        """Constructor method"""
        self.API_VERSION_MAJOR:int = API_VERSION_MAJOR
        """API major version"""
        self.API_VERSION_MINOR:int = API_VERSION_MINOR
        """API minor version"""

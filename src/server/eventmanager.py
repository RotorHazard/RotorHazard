'''
RotorHazard event manager
'''

import gevent

class EventManager:
    processEventObj = gevent.event.Event()

    events = {}
    eventOrder = {}
    eventThreads = {}

    def __init__(self):
        pass

    def on(self, event, name, handlerFn, defaultArgs=None, priority=200):
        if event not in self.events:
            self.events[event] = {}

        self.events[event][name] = {
            "handlerFn": handlerFn,
            "defaultArgs": defaultArgs,
            "priority": priority
        }

        self.eventOrder[event] = sorted(self.events[event].items(), key=lambda x: x[1]['priority'])

        return True

    def trigger(self, event, evtArgs=None):
        if event in self.events:
            for handlerlist in self.eventOrder[event]:
                for name in handlerlist:
                    handler = self.events[event][name]

                    args = handler['defaultArgs']
                    if evtArgs:
                        if args:
                            args.update(evtArgs)
                        else:
                            args = evtArgs

                    if handler['priority'] < 100:
                        # stop any threads with same name
                        if name in self.eventThreads:
                            if self.eventThreads[name] is not None:
                                self.eventThreads[name].kill()
                                self.eventThreads[name] = None

                        handler['handlerFn'](args)
                    else:
                        # restart thread with same name regardless of status
                        if name in self.eventThreads:
                            if self.eventThreads[name] is not None:
                                self.eventThreads[name].kill()

                        self.eventThreads[name] = gevent.spawn(handler['handlerFn'], args)

                    return True
        return False

class Evt:
    MANUAL = 'manual'
    RACESCHEDULE = 'raceSchedule'
    RACESTAGE = 'raceStage'
    RACESTART = 'raceStart'
    RACEFINISH = 'raceFinish'
    RACESTOP = 'raceStop'
    LAPSCLEAR = 'lapsClear'
    RACEWIN = 'raceWin'
    CROSSINGENTER = 'crossingEnter'
    CROSSINGEXIT = 'crossingExit'
    STARTUP = 'startup'
    SHUTDOWN = 'shutdown'

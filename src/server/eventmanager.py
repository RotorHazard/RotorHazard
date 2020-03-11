'''
RotorHazard event manager
'''

import gevent

class EventManager:
    processEventObj = gevent.event.Event()

    events = {}
    eventThreads = {}

    def __init__(self):
        pass

    def on(self, event, name, handlerFn, defaultArgs=None, direct=False):
        if event not in self.events:
            self.events[event] = {}

        self.events[event][name] = {
            "handlerFn": handlerFn,
            "defaultArgs": defaultArgs,
            "direct": direct
        }
        return True

    def trigger(self, event, evtArgs=None):
        if event in self.events:
            for name in self.events[event]:
                handler = self.events[event][name]

                args = handler['defaultArgs']
                if evtArgs:
                    if args:
                        args.update(evtArgs)
                    else:
                        args = evtArgs

                if handler['direct']:
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

'''
Events.trigger(Event.RACESTAGE, None)

Events.on(Event.RACESTAGE, 'LED', ledEffect(), {})

Events.on(Event.RACESTAGE, 'OSD', osdEffect)

Events.trigger(Evt.CROSSINGENTER, {
    'nodeIndex': node_index,
    'color': hexToColor(getOption('colorNode_' + str(node_index), '#ffffff'))
    })
'''

class Evt:
    MANUAL = 'maunaul'
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

'''
LED event manager
Wires events to handlers
'''

import gevent

class LEDEventManager:
    processEventObj = gevent.event.Event()

    events = {}
    eventHandlers = {}
    eventThread = None

    def __init__(self, strip, config):
        self.strip = strip
        self.config = config

    def isEnabled(self):
        return True

    def registerEventHandler(self, name, handlerFn, validEvents, defaultArgs=None):
        self.eventHandlers[name] = {
            "handlerFn": handlerFn,
            "validEvents": validEvents,
            "defaultArgs": defaultArgs
        }

    def setEventHandler(self, event, name):
        self.events[event] = name

    def event(self, event, eventArgs=None):
        if event in self.events:
            currentEvent = self.events[event]
            if currentEvent in self.eventHandlers:
                handler = self.eventHandlers[currentEvent]
                args = handler['defaultArgs']
                if eventArgs:
                    if args:
                        args.update(eventArgs)
                    else:
                        args = eventArgs

                # restart thread regardless of status
                if self.eventThread is not None:
                    self.eventThread.kill()

                self.eventThread = gevent.spawn(handler['handlerFn'], self.strip, self.config, args)

    def clear(self):
        self.eventHandlers['clear']['handlerFn'](self.strip, self.config)

class NoLEDHandler():
    def __init__(self):
        pass

    def isEnabled(self):
        return False

    def __getattr__(self, *args, **kwargs):
        def nothing(*args, **kwargs):
            pass
        return nothing


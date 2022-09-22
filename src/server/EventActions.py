import logging
import json
from eventmanager import Evt

class EventActions:
    def __init__(self, eventmanager, RHData, speakFn):
        self._RHData = RHData
        self.Events = eventmanager
        self.logger = logging.getLogger(self.__class__.__name__)
        self.speakFn = speakFn

        self.actions = []

        self.loadActions()
        self.Events.on(Evt.ALL, 'Actions', self.doActions)
        self.Events.on(Evt.OPTION_SET, 'Actions', self.loadActions)

    def loadActions(self):
        try:
            self.actions = json.loads(self._RHData.get_option('actions'))
        except:
            self.logger.warning("Can't load stored actions JSON")

    def doActions(self, args):
        for action in self.actions:
            if action['event'] == args['_eventName']:
                if action['effect'] == "speak":
                    self.speakFn(action['text'])

        # self.logger.info(args)

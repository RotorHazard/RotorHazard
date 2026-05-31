import logging
import json
from RHUtils import catchLogExceptionsWrapper, cleanVarName, getNumericEntry
from eventmanager import Evt
from typing import List
from RHUI import UIField

from FlaskAppObj import APP
APP.app_context().push()

class EventActions:
    eventActionsList = []
    effects = {}

    def __init__(self, eventmanager, RaceContext):
        self._racecontext = RaceContext
        self.Events = eventmanager
        self.logger = logging.getLogger(self.__class__.__name__)
        self._missing_effect_warned = set()

        self.Events.trigger(Evt.ACTIONS_INITIALIZE, {
            'register_fn': self.registerEffect
            })

        self.loadActions()
        self.Events.on(Evt.ALL, 'actions', self.doActions, {}, 200, True)
        self.Events.on(Evt.CONFIG_SET, 'actions', self.loadActions, {}, 200, True)

    def registerEffect(self, effect):
        self.effects[effect.name] = effect
        self._missing_effect_warned.discard(effect.name)
        return True

    def getRegisteredEffects(self):
        return self.effects

    def getEventActionsList(self):
        return self.eventActionsList

    def loadActions(self, _args=None):
        actionSetting = self._racecontext.serverconfig.get_item('USER', 'actions')
        if actionSetting:
            try:
                self.eventActionsList = json.loads(actionSetting)
            except:
                self.logger.error("Can't load stored actions JSON")
        else:
            self.logger.debug("No actions to load")

    def addEventAction(self, event, effect, text):
        item = { 'event': event, 'effect': effect, 'text': text }
        self.eventActionsList.append(item)
        self._racecontext.serverconfig.set_item('USER', 'actions', json.dumps(self.eventActionsList))

    def containsAction(self, event):
        for item in self.eventActionsList:
            if item.get('event') == event:
                return True
        return False

    @catchLogExceptionsWrapper
    def doActions(self, args):
        for action in self.eventActionsList:
            if action['event'] == args['_eventName']:
                self.runEffect(action, args)

    def runEffect(self, action, args):
        effect_name = action.get('effect')
        if not effect_name or effect_name not in self.effects:
            if effect_name:
                if effect_name not in self._missing_effect_warned:
                    self._missing_effect_warned.add(effect_name)
                    self.logger.warning("Skipping unregistered event action effect '{}' for event '{}' "
                                        "(plugin may not be installed on this timer)".format(
                                            effect_name, action.get('event', '?')))
                else:
                    self.logger.debug("Skipping unregistered event action effect '{}' for event '{}'".format(
                                        effect_name, action.get('event', '?')))
            else:
                self.logger.warning("Skipping event action with no effect for event '{}'".format(
                                    action.get('event', '?')))
            return
        self.logger.debug("Calling effect '{}', node {}".format(action, \
                            getNumericEntry(args, 'node_index', -1) + 1))
        self.effects[effect_name].runEffect(action, args)

class ActionEffect():
    def __init__(self, label, effect_fn, fields:List[UIField], name=None):
        if name is None:
            self.name = cleanVarName(label)
        else:
            self.name = name

        self.label = label
        self.effect_fn = effect_fn
        self.fields = fields

    @catchLogExceptionsWrapper
    def runEffect(self, action, args):
        APP.app_context().push()
        self.effect_fn(action, args)


import logging
import json
from RHUtils import catchLogExceptionsWrapper
from eventmanager import Evt

class EventActions:
    eventActionsList = []
    effects = {}

    def __init__(self, eventmanager, RHData):
        self._RHData = RHData
        self.Events = eventmanager
        self.logger = logging.getLogger(self.__class__.__name__)

        self.Events.trigger('actionsInitialize', {
            'registerFn': self.registerEffect
            })

        self.loadActions()
        self.Events.on(Evt.ALL, 'Actions', self.doActions, {}, 200, True)
        self.Events.on(Evt.OPTION_SET, 'Actions', self.loadActions, {}, 200, True)

    def registerEffect(self, effect):
        self.effects[effect.name] = effect
        return True

    def getRegisteredEffects(self):
        return self.effects

    def loadActions(self, _args=None):
        actionSetting = self._RHData.get_option('actions')
        if actionSetting:
            try:
                self.eventActionsList = json.loads(actionSetting)
            except:
                self.logger.error("Can't load stored actions JSON")
        else:
            self.logger.debug("No actions to load")

    def doActions(self, args):
        for action in self.eventActionsList:
            if action['event'] == args['_eventName']:
                self.effects[action['effect']].effectFn(action, args)
                self.logger.debug("Calling effect '{}' with {}".format(action, args))

class ActionEffect():
    def __init__(self, name, label, effectFn, fields):
        self.name = name
        self.label = label
        self.effectFn = effectFn
        self.fields = fields

def initializeEventActions(Events, RHData, RACE, emit_phonetic_text, emit_priority_message, \
                           Language, logger):
    eventActionsObj = None
    try:
        eventActionsObj = EventActions(Events, RHData)

        #register built-in effects
        @catchLogExceptionsWrapper
        def speakEffect(action, args):
            text = action['text']
            if 'node_index' in args:
                pilot = RHData.get_pilot(RACE.node_pilots[args['node_index']])
                text = text.replace('%PILOT%', pilot.spokenName())

            if 'heat_id' in args:
                heat = RHData.get_heat(args['heat_id'])
            else:
                heat = RHData.get_heat(RACE.current_heat)

            if heat.note:
                text = text.replace('%HEAT%', heat.note)
            else:
                text = text.replace('%HEAT%', Language.__("heat " + str(heat.id)))

            emit_phonetic_text(text)

        @catchLogExceptionsWrapper
        def messageEffect(action, args):
            text = action['text']
            if 'node_index' in args:
                pilot = RHData.get_pilot(RACE.node_pilots[args['node_index']])
                text = text.replace('%PILOT%', pilot.callsign)

            if 'heat_id' in args:
                heat = RHData.get_heat(args['heat_id'])
            else:
                heat = RHData.get_heat(RACE.current_heat)

            if heat.note:
                text = text.replace('%HEAT%', heat.note)
            else:
                text = text.replace('%HEAT%', Language.__("heat " + str(heat.id)))

            emit_priority_message(text)

        @catchLogExceptionsWrapper
        def alertEffect(action, args):
            text = action['text']
            if 'node_index' in args:
                pilot = RHData.get_pilot(RACE.node_pilots[args['node_index']])
                text = text.replace('%PILOT%', pilot.callsign)

            if 'heat_id' in args:
                heat = RHData.get_heat(args['heat_id'])
            else:
                heat = RHData.get_heat(RACE.current_heat)

            if heat.note:
                text = text.replace('%HEAT%', heat.note)
            else:
                text = text.replace('%HEAT%', Language.__("heat " + str(heat.id)))

            emit_priority_message(text, True)

        eventActionsObj.registerEffect(
            ActionEffect(
                'speak', 
                'Speak',
                speakEffect, 
                [
                    {
                        'id': 'text',
                        'name': 'Callout Text',
                        'type': 'text',
                    }
                ]
            )
        )
        eventActionsObj.registerEffect(
            ActionEffect(
                'message',
                'Message',
                messageEffect,
                [
                    {
                        'id': 'text',
                        'name': 'Message Text',
                        'type': 'text',
                    }
                ]
            )
        )
        eventActionsObj.registerEffect(
            ActionEffect(
                'alert',
                'Alert',
                 alertEffect,
                [
                    {
                        'id': 'text',
                        'name': 'Alert Text',
                        'type': 'text',
                    }
                ]
            )
        )

    except Exception:
        logger.exception("Error loading EventActions")

    return eventActionsObj

''' builtin Actions '''

import json
import RHUtils
from eventmanager import Evt
from EventActions import ActionEffect
from RHUI import UIField, UIFieldType, UIFieldSelectOption

class ActionsBuiltin():
    def __init__(self, rhapi):
        self._rhapi = rhapi

    def speakEffect(self, action, args):
        if 'text' in action:
            text = RHUtils.doReplace(self._rhapi, action['text'], args, True)
            self._rhapi.ui.message_speak(text)

    def messageEffect(self, action, args):
        if 'text' in action:
            text = RHUtils.doReplace(self._rhapi, action['text'], args)
            self._rhapi.ui.message_notify(text)

    def alertEffect(self, action, args):
        if 'text' in action:
            text = RHUtils.doReplace(self._rhapi, action['text'], args)
            self._rhapi.ui.message_alert(text)

    def scheduleEffect(self, action, _args):
        if 'sec' in action:
            if 'min' in action:
                self._rhapi.race.schedule(action['sec'], action['min'])
            else:
                self._rhapi.race.schedule(action['sec'])

    def register_handlers(self, args):
        for effect in [
            ActionEffect(
                "Speak",
                self.speakEffect,
                [
                    UIField('text', "Callout Text", UIFieldType.TEXT),
                ]
            ),
            ActionEffect(
                "Message",
                self.messageEffect,
                [
                    UIField('text', "Message Text", UIFieldType.TEXT),
                ]
            ),
            ActionEffect(
                "Alert",
                self.alertEffect,
                [
                    UIField('text', "Alert Text", UIFieldType.TEXT),
                ]
            ),
            ActionEffect(
                "Schedule Race",
                self.scheduleEffect,
                [
                    UIField('sec', "Seconds", UIFieldType.BASIC_INT),
                    UIField('min', "Minutes", UIFieldType.BASIC_INT),
                ]
            )
        ]:
            args['register_fn'](effect)

def initialize(rhapi):
    actions = ActionsBuiltin(rhapi)
    rhapi.events.on(Evt.ACTIONS_INITIALIZE, actions.register_handlers)


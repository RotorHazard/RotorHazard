''' builtin Actions '''

import RHData
import gevent
from eventmanager import Evt
from EventActions import ActionEffect
from RHUI import UIField, UIFieldType, UIFieldSelectOption

from FlaskAppObj import APP
APP.app_context().push()

class ActionsBuiltin():
    def __init__(self, rhapi):
        self._rhapi = rhapi

    def speakEffect(self, action, args):
        if 'text' in action:
            delay_sec_holder = []  # will be filled if "%DELAY_#_SECS%" or %PILOTS_INTERVAL_#_SECS% provided
            text = RHData.doReplace(self._rhapi, action['text'], args, True, delay_sec_holder)
            if len(delay_sec_holder) <= 0 or not isinstance(delay_sec_holder[0], float):
                self._rhapi.ui.message_speak(text)
            else:
                if not isinstance(text, list):
                    gevent.spawn_later(delay_sec_holder[0], self._rhapi.ui.message_speak, text)
                else:
                    for i, piece in enumerate(text):
                        gevent.spawn_later(delay_sec_holder[0]*(i+1), self._rhapi.ui.message_speak, piece)

    def messageEffect(self, action, args):
        if 'text' in action:
            text = RHData.doReplace(self._rhapi, action['text'], args)
            self._rhapi.ui.message_notify(text)

    def alertEffect(self, action, args):
        if 'text' in action:
            text = RHData.doReplace(self._rhapi, action['text'], args)
            self._rhapi.ui.message_alert(text)


    def clearMessagesEffect(self, action, args):
        self._rhapi.ui.clear_messages()
        if 'text' in action:
            text = RHData.doReplace(self._rhapi, action['text'], args)
            self._rhapi.ui.message_notify(text)

    def scheduleEffect(self, action, _args):
        try:
            secs = int(action.get('sec'))
        except:
            secs = 0

        try:
            mins = int(action.get('min'))
        except:
            mins = 0

        if secs or mins:
            self._rhapi.race.schedule(secs, mins)

    def register_handlers(self, args):
        for effect in [
            ActionEffect(
                "Speak",
                self.speakEffect,
                [
                    UIField('text', "Callout Text", UIFieldType.TEXT),
                ],
                name='speak',
            ),
            ActionEffect(
                "Message",
                self.messageEffect,
                [
                    UIField('text', "Message Text", UIFieldType.TEXT),
                ],
                name='message',
            ),
            ActionEffect(
                "Alert",
                self.alertEffect,
                [
                    UIField('text', "Alert Text", UIFieldType.TEXT),
                ],
                name='alert',
            ),
            ActionEffect(
                "Clear Messages",
                self.clearMessagesEffect,
                [
                    UIField('text', "Message Text (optional)", UIFieldType.TEXT),
                ],
                name='clearMessages',
            ),
            ActionEffect(
                "Schedule Race",
                self.scheduleEffect,
                [
                    UIField('sec', "Seconds", UIFieldType.BASIC_INT),
                    UIField('min', "Minutes", UIFieldType.BASIC_INT),
                ],
                name='schedule',
            )
        ]:
            args['register_fn'](effect)

def initialize(rhapi):
    actions = ActionsBuiltin(rhapi)
    rhapi.events.on(Evt.ACTIONS_INITIALIZE, actions.register_handlers)


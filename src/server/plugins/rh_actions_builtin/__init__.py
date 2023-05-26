''' builtin Actions '''

from EventActions import ActionEffect

class ActionsBuiltin():
    def __init__(self, RHAPI):
        self._RHAPI = RHAPI

    def doReplace(self, text, args):
        # %PILOT%
        if 'node_index' in args:
            pilot = self._RHAPI.get_pilot(self._RHAPI.race_pilots[args['node_index']])
            text = text.replace('%PILOT%', pilot.spokenName())

        # %HEAT%
        if 'heat_id' in args:
            heat = self._RHAPI.get_heat(args['heat_id'])
        else:
            heat = self._RHAPI.get_heat(self._RHAPI.race_heat)

        text = text.replace('%HEAT%', heat.displayname())

        return text

    def speakEffect(self, action, args):
        if 'text' in action:
            text = self.doReplace(action['text'], args)
            self._RHAPI.emit_phonetic_text(text)

    def messageEffect(self, action, args):
        if 'text' in action:
            text = self.doReplace(action['text'], args)
            self._RHAPI.emit_priority_message(text)

    def alertEffect(self, action, args):
        if 'text' in action:
            text = self.doReplace(action['text'], args)
            self._RHAPI.emit_priority_message(text, True)


actions = None

def initialize(**kwargs):
    if 'Events' in kwargs:
        kwargs['Events'].on('actionsInitialize', 'action_builtin', registerHandlers, {}, 75)

    global actions
    actions = ActionsBuiltin(kwargs['RHAPI'])

def registerHandlers(args):
    if 'registerFn' in args:
        for effect in discover():
            args['registerFn'](effect)

def discover():
    return [
        ActionEffect(
            'speak',
            'Speak',
            actions.speakEffect,
            [
                {
                    'id': 'text',
                    'name': 'Callout Text',
                    'type': 'text',
                }
            ]
        ),
        ActionEffect(
            'message',
            'Message',
            actions.messageEffect,
            [
                {
                    'id': 'text',
                    'name': 'Message Text',
                    'type': 'text',
                }
            ]
        ),
        ActionEffect(
            'alert',
            'Alert',
            actions.alertEffect,
            [
                {
                    'id': 'text',
                    'name': 'Alert Text',
                    'type': 'text',
                }
            ]
        )
    ]
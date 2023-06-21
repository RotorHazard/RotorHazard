''' builtin Actions '''

from EventActions import ActionEffect
from RHUI import UIField, UIFieldType, UIFieldSelectOption

class ActionsBuiltin():
    def __init__(self, RHAPI):
        self._rhapi = RHAPI

    def doReplace(self, text, args):
        # %HEAT%
        if 'heat_id' in args:
            heat = self._rhapi.db.heat_by_id(args['heat_id'])
        else:
            heat = self._rhapi.db.heat_by_id(self._rhapi.race.heat)

        text = text.replace('%HEAT%', heat.display_name())

        if 'results' in args:
            leaderboard = args['results'][args['results']['meta']['primary_leaderboard']]
            
            for result in leaderboard:
                if result['node'] == args['node_index']:
                    # %LAP_COUNT%
                    text = text.replace('%LAP_COUNT%', str(result['laps']))

                    # %TOTAL_TIME%
                    text = text.replace('%TOTAL_TIME%', result['total_time'])

                    # %TOTAL_TIME_LAPS%
                    text = text.replace('%TOTAL_TIME_LAPS%', result['total_time_laps'])

                    # %LAST_LAP%
                    text = text.replace('%LAST_LAP%', result['last_lap'])

                    # %AVERAGE_LAP%
                    text = text.replace('%AVERAGE_LAP%', result['average_lap'])

                    # %FASTEST_LAP%
                    text = text.replace('%FASTEST_LAP%', result['fastest_lap'])

                    # %CONSECUTIVE%
                    if result['consecutives_base'] == int(self._rhapi.db.option('consecutivesCount', 3)):
                        text = text.replace('%CONSECUTIVE%', result['consecutives'])
                    else:
                        text = text.replace('%CONSECUTIVE%', self._rhapi.__('None'))

                    # %POSITION%
                    text = text.replace('%POSITION%', str(result['position']))

                    break

        return text

    def speakEffect(self, action, args):
        if 'text' in action:
            text = self.doReplace(action['text'], args)

            # %PILOT%
            if 'node_index' in args:
                pilot = self._rhapi.db.pilot_by_id(self._rhapi.race.pilots[args['node_index']])
                text = text.replace('%PILOT%', pilot.spoken_callsign())

            self._rhapi.ui.message_speak(text)

    def messageEffect(self, action, args):
        if 'text' in action:
            text = self.doReplace(action['text'], args)

            # %PILOT%
            if 'node_index' in args:
                pilot = self._rhapi.db.pilot_by_id(self._rhapi.race.pilots[args['node_index']])
                text = text.replace('%PILOT%', pilot.display_callsign())

            self._rhapi.ui.message_notify(text)

    def alertEffect(self, action, args):
        if 'text' in action:
            text = self.doReplace(action['text'], args)

            # %PILOT%
            if 'node_index' in args:
                pilot = self._rhapi.db.pilot_by_id(self._rhapi.race.pilots[args['node_index']])
                text = text.replace('%PILOT%', pilot.display_callsign())

            self._rhapi.ui.message_alert(text)

    def scheduleEffect(self, action, args):
        if 'sec' in action:
            if 'min' in action:
                self._rhapi.race.schedule(action['sec'], action['min'])
            else:
                self._rhapi.race.schedule(action['sec'])

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
                UIField('text', "Callout Text", UIFieldType.TEXT),
            ]
        ),
        ActionEffect(
            'message',
            'Message',
            actions.messageEffect,
            [
                UIField('text', "Message Text", UIFieldType.TEXT),
            ]
        ),
        ActionEffect(
            'alert',
            'Alert',
            actions.alertEffect,
            [
                UIField('text', "Alert Text", UIFieldType.TEXT),
            ]
        ),
        ActionEffect(
            'schedule',
            'Schedule Race',
            actions.scheduleEffect,
            [
                UIField('sec', "Seconds", UIFieldType.BASIC_INT),
                UIField('min', "Minutes", UIFieldType.BASIC_INT),
            ]
        )
    ]


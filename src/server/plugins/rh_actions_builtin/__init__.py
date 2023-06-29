''' builtin Actions '''

import json
import RHUtils
from eventmanager import Evt
from EventActions import ActionEffect
from RHUI import UIField, UIFieldType, UIFieldSelectOption

class ActionsBuiltin():
    def __init__(self, rhapi):
        self._rhapi = rhapi

    def doReplace(self, text, args, spoken_flag=False):
        if '%' in text:
            # %HEAT%
            if 'heat_id' in args:
                heat = self._rhapi.db.heat_by_id(args['heat_id'])
            else:
                heat = self._rhapi.db.heat_by_id(self._rhapi.race.heat)
            text = text.replace('%HEAT%', heat.display_name if heat and heat.display_name else self._rhapi.__('None'))

            if 'node_index' in args:
                pilot = self._rhapi.db.pilot_by_id(self._rhapi.race.pilots[args['node_index']])
                text = text.replace('%PILOT%', pilot.spoken_callsign if spoken_flag else pilot.display_callsign)
    
            if 'results' in args:
                race_results = args['results']
                if 'node_index' in args and '%' in text:
                    lboard_name = race_results.get('meta', {}).get('primary_leaderboard', '')
                    leaderboard = race_results.get(lboard_name, [])

                    for result in leaderboard:
                        if result['node'] == args['node_index']:
                            # %LAP_COUNT%
                            text = text.replace('%LAP_COUNT%', str(result['laps']))

                            # %TOTAL_TIME%
                            text = text.replace('%TOTAL_TIME%', RHUtils.phonetictime_format( \
                                        result['total_time_raw'], self._rhapi.db.option('timeFormatPhonetic')) \
                                        if spoken_flag else result['total_time'])

                            # %TOTAL_TIME_LAPS%
                            text = text.replace('%TOTAL_TIME_LAPS%', RHUtils.phonetictime_format( \
                                        result['total_time_laps_raw'], self._rhapi.db.option('timeFormatPhonetic')) \
                                        if spoken_flag else result['total_time_laps'])

                            # %LAST_LAP%
                            text = text.replace('%LAST_LAP%', RHUtils.phonetictime_format( \
                                        result['last_lap_raw'], self._rhapi.db.option('timeFormatPhonetic')) \
                                        if spoken_flag else result['last_lap'])

                            # %AVERAGE_LAP%
                            text = text.replace('%AVERAGE_LAP%', RHUtils.phonetictime_format( \
                                        result['average_lap_raw'], self._rhapi.db.option('timeFormatPhonetic')) \
                                        if spoken_flag else result['average_lap'])

                            # %FASTEST_LAP%
                            text = text.replace('%FASTEST_LAP%', RHUtils.phonetictime_format( \
                                        result['fastest_lap_raw'], self._rhapi.db.option('timeFormatPhonetic')) \
                                        if spoken_flag else result['fastest_lap'])

                            # %CONSECUTIVE%
                            if result['consecutives_base'] == int(self._rhapi.db.option('consecutivesCount', 3)):
                                text = text.replace('%CONSECUTIVE%', RHUtils.phonetictime_format( \
                                        result['consecutives_raw'], self._rhapi.db.option('timeFormatPhonetic')) \
                                        if spoken_flag else result['consecutives'])
                            else:
                                text = text.replace('%CONSECUTIVE%', self._rhapi.__('None'))

                            # %POSITION%
                            text = text.replace('%POSITION%', str(result['position']))

                            break

                if '%FASTEST_RACE_LAP' in text:
                    fastest_race_lap_data = race_results.get('meta', {}).get('fastest_race_lap_data')
                    if fastest_race_lap_data:
                        if spoken_flag:
                            fastest_str = "{}, {}".format(fastest_race_lap_data['phonetic'][0],  # pilot name
                                                          fastest_race_lap_data['phonetic'][1])  # lap time
                        else:
                            fastest_str = "{} {}".format(fastest_race_lap_data['text'][0],  # pilot name
                                                         fastest_race_lap_data['text'][1])  # lap time
                    else:
                        fastest_str = ""
                    # %FASTEST_RACE_LAP% : Pilot/time for fastest lap in race
                    text = text.replace('%FASTEST_RACE_LAP%', fastest_str)
                    # %FASTEST_RACE_LAP_CALL% : Pilot/time for fastest lap in race (with prompt)
                    if len(fastest_str) > 0:
                        fastest_str = "{} {}".format(self._rhapi.__('Fastest lap'), fastest_str)
                    text = text.replace('%FASTEST_RACE_LAP_CALL%', fastest_str)

                if '%PILOTS%' in text:
                    text = text.replace('%PILOTS%', self.getPilotsListStr(' . ', spoken_flag))
                if '%LINEUP%' in text:
                    text = text.replace('%LINEUP%', self.getPilotsListStr(' , ', spoken_flag))
                if '%FREQS%' in text:
                    text = text.replace('%FREQS%', self.getPilotFreqsStr(' . ', spoken_flag))

        return text

    def speakEffect(self, action, args):
        if 'text' in action:
            text = self.doReplace(action['text'], args, True)
            self._rhapi.ui.message_speak(text)

    def messageEffect(self, action, args):
        if 'text' in action:
            text = self.doReplace(action['text'], args)
            self._rhapi.ui.message_notify(text)

    def alertEffect(self, action, args):
        if 'text' in action:
            text = self.doReplace(action['text'], args)
            self._rhapi.ui.message_alert(text)

    def scheduleEffect(self, action, args):
        if 'sec' in action:
            if 'min' in action:
                self._rhapi.race.schedule(action['sec'], action['min'])
            else:
                self._rhapi.race.schedule(action['sec'])

    def heatNodeSorter(self, x):
        if not x.node_index:
            return -1
        return x.node_index

    def getPilotsListStr(self, sep_str, spoken_flag):
        pilots_str = ''
        first_flag = True
        heat_nodes = self._rhapi.db.slots_by_heat(self._rhapi.race.heat)
        heat_nodes.sort(key=self.heatNodeSorter)
        for heat_node in heat_nodes:
            pilot = self._rhapi.db.pilot_by_id(heat_node.pilot_id)
            if pilot:
                text = pilot.spoken_callsign if spoken_flag else pilot.display_callsign
                if text:
                    if first_flag:
                        first_flag = False
                    else:
                        pilots_str += sep_str
                    pilots_str += text
        return pilots_str

    def getPilotFreqsStr(self, sep_str, spoken_flag):
        pilots_str = ''
        first_flag = True
        heat_nodes = self._rhapi.db.slots_by_heat(self._rhapi.race.heat)
        heat_nodes.sort(key=self.heatNodeSorter)
        for heat_node in heat_nodes:
            pilot = self._rhapi.db.pilot_by_id(heat_node.pilot_id)
            if pilot:
                text = pilot.spoken_callsign if spoken_flag else pilot.display_callsign
                if text:
                    profile_freqs = json.loads(self._rhapi.race.frequencyset.frequencies)
                    if profile_freqs:
                        freq = str(profile_freqs["b"][heat_node.node_index]) + str(profile_freqs["c"][heat_node.node_index])
                        if freq:
                            if first_flag:
                                first_flag = False
                            else:
                                pilots_str += sep_str
                            pilots_str += text + ': ' + freq
        return pilots_str

def register_handlers(args):
    for effect in [
        ActionEffect(
            'speak',
            "Speak",
            actions.speakEffect,
            [
                UIField('text', "Callout Text", UIFieldType.TEXT),
            ]
        ),
        ActionEffect(
            'message',
            "Message",
            actions.messageEffect,
            [
                UIField('text', "Message Text", UIFieldType.TEXT),
            ]
        ),
        ActionEffect(
            'alert',
            "Alert",
            actions.alertEffect,
            [
                UIField('text', "Alert Text", UIFieldType.TEXT),
            ]
        ),
        ActionEffect(
            'schedule',
            "Schedule Race",
            actions.scheduleEffect,
            [
                UIField('sec', "Seconds", UIFieldType.BASIC_INT),
                UIField('min', "Minutes", UIFieldType.BASIC_INT),
            ]
        )
    ]:
        args['register_fn'](effect)

actions = None

def initialize(**kwargs):
    kwargs['events'].on(Evt.ACTIONS_INITIALIZE, 'action_builtin', register_handlers, {}, 75)

    global actions
    actions = ActionsBuiltin(kwargs['rhapi'])


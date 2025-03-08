''' Trackside Connector '''

import logging
import json
from time import monotonic
from RHRace import RaceStatus
from eventmanager import Evt
from RHUI import UIField, UIFieldType, UIFieldSelectOption

logger = logging.getLogger(__name__)

class TracksideConnector():
    def __init__(self, rhapi):
        self._rhapi = rhapi
        self.enabled = False
        self._trackside_race_id = None

        self._rhapi.events.on(Evt.RACE_LAP_RECORDED, self.race_lap_recorded)
        self._rhapi.events.on(Evt.LAPS_SAVE, self.laps_save)
        self._rhapi.events.on(Evt.LAPS_CLEAR, self.laps_clear)
        self._rhapi.events.on(Evt.LAPS_RESAVE, self.laps_resave)


    def initialize(self, _args):
        logger.info('Initializing Trackside connector')

        self._rhapi.ui.socket_listen('ts_server_info', self.server_info)
        self._rhapi.ui.socket_listen('ts_server_time', self.server_time)
        self._rhapi.ui.socket_listen('ts_frequency_setup', self.frequency_setup)
        self._rhapi.ui.socket_listen('ts_color_setup', self.color_setup)

        self._rhapi.ui.socket_listen('ts_race_stage', self.race_stage)
        self._rhapi.ui.socket_listen('ts_race_stop', self.race_stop)

        self._rhapi.fields.register_race_attribute(UIField('trackside_race_ID', "FPVTrackSide Race ID", UIFieldType.TEXT, private=True))
        self._rhapi.fields.register_pilot_attribute(UIField('trackside_pilot_ID', "Trackside Pilot ID", UIFieldType.TEXT, private=True))

    def server_info(self, _arg=None):
        self.enabled = True
        info = {
            'name': self._rhapi.config.get('UI', 'timerName'),
            'logo': self._rhapi.config.get('UI', 'timerLogo'),
            'hue_primary': self._rhapi.config.get('UI', 'hue_0'),
            'sat_primary': self._rhapi.config.get('UI', 'sat_0'),
            'lum_primary': self._rhapi.config.get('UI', 'lum_0_low'),
            'contrast_primary': self._rhapi.config.get('UI', 'contrast_0_low'),
            'hue_secondary': self._rhapi.config.get('UI', 'hue_1'),
            'sat_secondary': self._rhapi.config.get('UI', 'sat_1'),
            'lum_secondmary': self._rhapi.config.get('UI', 'lum_1_low'),
            'contrast_secondmary': self._rhapi.config.get('UI', 'contrast_1_low'),
        }
        info.update(self._rhapi.server_info)
        return info

    def server_time(self, _arg=None):
        self.enabled = True
        return monotonic()

    def frequency_setup(self, arg=None):
        self.enabled = True
        frequency_set = self._rhapi.race.frequencyset
        self._rhapi.db.frequencyset_alter(frequency_set.id, frequencies=arg)

    def race_stage(self, arg=None):
        if not arg:
            return None

        self.enabled = True

        if self._rhapi.race.status != RaceStatus.READY:
            self._rhapi.race.stop(doSave=True) # Stop and save in one operation, which triggers Save and Clear

        if arg.get('p'):
            heat = self._rhapi.db.heat_add()
            self._rhapi.db.heat_alter(heat.id, name="TrackSide Heat {}".format(heat.id))
            slots = self._rhapi.db.slots_by_heat(heat.id)
            slot_list = []

            ts_pilot_callsigns = arg.get('p')
            ts_pilot_ids = arg.get('p_id')
            rh_pilots = self._rhapi.db.pilots
            added_pilot = False
            for idx, ts_pilot_callsign in enumerate(ts_pilot_callsigns):
                ts_id = ts_pilot_ids[idx] if ts_pilot_ids and idx < len(ts_pilot_ids) else None
                for rh_pilot in rh_pilots:
                    rh_pilot_ts_id = self._rhapi.db.pilot_attribute_value(rh_pilot.id, 'trackside_pilot_ID', None)
                    if ts_id and rh_pilot_ts_id == ts_id:
                        pilot = rh_pilot
                        break
                    else:
                        if rh_pilot.callsign == ts_pilot_callsign:
                            pilot = rh_pilot
                            break
                else:
                    new_pilot = self._rhapi.db.pilot_add(name=ts_pilot_callsign, callsign=ts_pilot_callsign)
                    self._rhapi.db.pilot_alter(new_pilot.id, attributes={
                        'trackside_pilot_ID': ts_id
                    })
                    pilot = new_pilot
                    added_pilot = True

                for slot in slots:
                    if slot.node_index == idx:
                        slot_list.append({
                            'slot_id': slot.id,
                            'pilot': pilot.id
                        })
                        break

            self._rhapi.db.slots_alter_fast(slot_list)
            self._rhapi.race.heat = heat.id

            if added_pilot:
                self._rhapi.ui.broadcast_pilots()
            self._rhapi.ui.broadcast_heats()
            self._rhapi.ui.broadcast_current_heat()

        start_race_args = {
            'secondary_format': True,
            'ignore_secondary_heat': True,
        }

        if arg.get('start_time_s'):
            start_race_args['start_time_s'] = arg['start_time_s']

        self._trackside_race_id = arg.get('race_id')

        self._rhapi.race.stage(start_race_args)

    def race_lap_recorded(self, args):
        if self.enabled:
            payload = {
                'seat': args['node_index'],
                'frequency': args['frequency'],
                'peak_rssi': args['peak_rssi'],
                'lap_time': args['lap'].lap_time_stamp / 1000,
            }
            self._rhapi.ui.socket_broadcast('ts_lap_data', payload)

    def race_stop(self, arg=None):
        self._rhapi.race.stop(doSave=True) # Stop and save in one operation, which triggers Save and Clear

    def laps_save(self, args):
        race_id = args.get('race_id')
        if race_id and self._trackside_race_id:
            self._rhapi.db.race_alter(race_id, attributes = {
                'trackside_race_ID': self._trackside_race_id
            })

    def laps_clear(self, args):
        self._trackside_race_id = None

    def laps_resave(self, args):
        if args and args.get('race_id'):
            race_id = args.get('race_id')
            for run in self._rhapi.db.pilotruns_by_race(race_id):
                if run.pilot_id == args.get('pilot_id'):
                    laps_raw = self._rhapi.db.laps_by_pilotrun(run.id)
                    laps = []
                    for lap in laps_raw:
                        laps.append({
                            'deleted': lap.deleted,
                            'lap_time': lap.lap_time,
                            'lap_time_formatted': lap.lap_time_formatted,
                            'lap_time_stamp': lap.lap_time_stamp,
                        })    
                    break
            else:
                return False

            ts_race_id = self._rhapi.db.race_attribute_value(race_id, 'trackside_race_ID')

            pilot_id = args.get('pilot_id')
            callsign = self._rhapi.db.pilot_by_id(pilot_id).callsign
            ts_pilot_id = self._rhapi.db.pilot_attribute_value(pilot_id, 'trackside_pilot_ID', None)

            payload = {
                'race_id': ts_race_id,
                'callsign': callsign,
                'ts_pilot_id': ts_pilot_id,
                'laps': laps
            }
            self._rhapi.ui.socket_broadcast('ts_race_marshal', payload)

    def color_setup(self, arg):
        if arg.get('channel_color'):
            self._rhapi.config.set('LED', 'ledColorMode', 0)  # TS supports only "seat" mode
            self._rhapi.config.set('LED', 'seatColors', arg.get('channel_color'))
            self._rhapi.race.update_colors()
            self._rhapi.ui.broadcast_pilots()
            self._rhapi.ui.broadcast_heats()

def initialize(rhapi):
    connector = TracksideConnector(rhapi)
    rhapi.events.on(Evt.STARTUP, connector.initialize)


'''JSON data importer'''

import logging
import json
import RHUtils
import Database
from eventmanager import Evt
from data_import import DataImporter
from Database import ProgramMethod
from RHUI import UIField, UIFieldType, UIFieldSelectOption

logger = logging.getLogger(__name__)

def import_json(rhapi, source, args):
    if not source:
        return False

    try:
        data = json.loads(source)
    except Exception as ex:
        logger.error("Unable to import file: {}".format(str(ex)))
        return False

    if 'Pilot' in data:
        logger.debug("Importing Pilots...")

        if 'reset_pilots' in args and args['reset_pilots']:
            rhapi.db.pilots_clear()

        db_pilots = rhapi.db.pilots

        for input_pilot in data['Pilot']:

            source_id = input_pilot['id']

            db_match = None
            for db_pilot in db_pilots:
                if db_pilot.callsign == input_pilot['callsign']:
                    db_match = db_pilot
                    break

            for item in list(input_pilot.keys()):
                if item not in ['name', 
                    'callsign',
                    'phonetic',
                    'team',
                    'color', 
                    'attributes'
                    ]:
                    del input_pilot[item]

            if db_match:
                db_pilot, _ = rhapi.db.pilot_alter(db_match.id, **input_pilot)
            else:
                if 'attributes' in input_pilot:
                    del input_pilot['attributes']

                db_pilot = rhapi.db.pilot_add(**input_pilot)

            input_pilot['source_id'] = source_id
            input_pilot['db_id'] = db_pilot.id

    if 'RaceFormat' in data:
        logger.debug("Importing Formats...")

        if 'reset_formats' in args and args['reset_formats']:
            rhapi.db.raceformats_clear()

        db_formats = rhapi.db.raceformats

        for input_format in data['RaceFormat']:
            db_match = None
            for db_format in db_formats:
                if db_format.name == input_format['name']:
                    db_match = db_format
                    break

            for item in list(input_format.keys()):
                if item not in [
                    'name', 
                    'unlimited_time', 
                    'race_time_sec', 
                    'lap_grace_sec', 
                    'staging_fixed_tones', 
                    'staging_delay_tones', 
                    'start_delay_min_ms', 
                    'start_delay_max_ms', 
                    'start_behavior', 
                    'win_condition', 
                    'number_laps_win', 
                    'team_racing_mode', 
                    'points_method'
                    ]:
                    del input_format[item]

            if db_match:
                db_format, _ = rhapi.db.raceformat_alter(db_match.id, **input_format)
            else:
                db_format = rhapi.db.raceformat_add(**input_format)

            input_format['db_id'] = db_format.id

    if 'Profiles' in data:
        logger.debug("Importing Profiles...")

        if 'reset_profiles' in args and args['reset_profiles']:
            rhapi.db.frequencysets_clear()

        db_profiles = rhapi.db.frequencysets

        for input_profile in data['Profiles']:
            db_match = None
            for db_profile in db_profiles:
                if db_profile.name == input_profile['name']:
                    db_match = db_profile
                    break

            for item in list(input_profile.keys()):
                if item not in [
                    'name',
                    'description',
                    'frequencies',
                    'enter_ats',
                    'exit_ats'
                    ]:
                    del input_profile[item]

            if db_match:
                db_profile = rhapi.db.frequencyset_alter(db_match.id, **input_profile)
            else:
                db_profile = rhapi.db.frequencyset_add(**input_profile)

            input_profile['db_id'] = db_profile.id

    if 'GlobalSettings' in data:
        logger.debug("Importing Settings...")

        invalid_settings = [
            'server_api',
            'secret_key',
            'currentProfile',
            'currentFormat',
            'eventResults',
            'eventResults_cacheStatus',
        ]

        for setting in data['GlobalSettings']:
            if setting['option_name'] not in invalid_settings:
                rhapi.db.option_set(setting['option_name'], setting['option_value'])

    if 'RaceClass' in data:
        logger.debug("Importing Classes/Heats...")

        if 'reset_classes' in args and args['reset_classes']:
            rhapi.db.heats_clear()
            rhapi.db.raceclasses_clear()
            rhapi.db.races_clear()

        db_race_classes = rhapi.db.raceclasses

        for input_race_class in data['RaceClass']:
            db_match = None
            for db_race_class in db_race_classes:
                if db_race_class.name == input_race_class['name']:
                    db_match = db_race_class
                    break

            source_id = input_race_class['id']

            input_race_class['raceformat'] = input_race_class['format_id'] # db_id

            for item in list(input_race_class.keys()):
                if item not in [
                    'name',
                    'description',
                    'raceformat',
                    'win_condition',
                    'rounds',
                    'heat_advance_type',
                    'rank_settings'
                    ]:
                    del input_race_class[item]

            if db_match:
                db_race_class, _ = rhapi.db.raceclass_alter(db_match.id, **input_race_class)
            else:
                if 'rank_settings' in input_race_class:
                    del input_race_class['rank_settings']

                db_race_class = rhapi.db.raceclass_add(**input_race_class)

            input_race_class['source_id'] = source_id
            input_race_class['db_id'] = db_race_class.id

            if 'Heat' in data:
                for input_heat in data['Heat']:
                    if input_heat.get('class_id') and input_heat['class_id'] == input_race_class['source_id']:
                        source_id = input_heat['id']

                        input_heat['raceclass'] = input_race_class['db_id']

                        for item in list(input_heat.keys()):
                            if item not in [
                                'name',
                                'raceclass',
                                'auto_frequency',
                                ]:
                                del input_heat[item]

                        db_heat = rhapi.db.heat_add(**input_heat)

                        input_heat['source_id'] = source_id
                        input_heat['db_id'] = db_heat.id

    if 'HeatNode' in data and 'Heat' in data and 'RaceClass' in data:
        logger.debug("Updating HeatNodes...")

        batch = []

        for input_heatnode in data['HeatNode']:
            db_heatnodes = rhapi.db.slots

            for heat in data['Heat']:
                if 'source_id' in heat and heat['source_id'] == input_heatnode['heat_id']:
                    for heatnode in db_heatnodes:
                        if heatnode.heat_id == heat['db_id'] and heatnode.node_index == input_heatnode['node_index']: 
                            input_heatnode['slot_id'] = heatnode.id 

                            if input_heatnode['method'] == ProgramMethod.ASSIGN:
                                input_heatnode['pilot'] = RHUtils.PILOT_ID_NONE
                                if 'Pilot' in data:
                                    for p in data['Pilot']:
                                        if p['source_id'] == input_heatnode['pilot_id']:
                                            input_heatnode['pilot'] = p['db_id']
                                            break
                            elif input_heatnode['method'] == ProgramMethod.HEAT_RESULT:
                                for h in data['Heat']:
                                    if h['source_id'] == input_heatnode['seed_id']:
                                        input_heatnode['seed_heat_id'] = h['db_id']
                                        break

                            elif input_heatnode['method'] == ProgramMethod.CLASS_RESULT:
                                for c in data['RaceClass']:
                                    if c['source_id'] == input_heatnode['seed_id']:
                                        input_heatnode['seed_raceclass_id'] = c['db_id']
                                        break

                            for item in list(input_heatnode.keys()):
                                if item not in [
                                    'slot_id',
                                    'pilot',
                                    'method',
                                    'seed_heat_id',
                                    'seed_raceclass_id',
                                    'seed_rank'
                                    ]:
                                    del input_heatnode[item]

                            batch.append(input_heatnode)
                            break
                    break

            rhapi.db.slots_alter_fast(batch)

    return True

def register_handlers(args):
    for importer in [
        DataImporter(
            'json',
            'RotorHazard 4.0 JSON',
            import_json,
            None,
            [
                UIField('reset_pilots', "Reset Pilots", UIFieldType.CHECKBOX, value=False),
                UIField('reset_formats', "Reset Formats", UIFieldType.CHECKBOX, value=False),
                UIField('reset_profiles', "Reset Profiles", UIFieldType.CHECKBOX, value=False),
                UIField('reset_classes', "Reset Classes and Race Data", UIFieldType.CHECKBOX, value=False),
            ]
        ),
    ]:
        args['register_fn'](importer)

def initialize(**kwargs):
    kwargs['events'].on(Evt.DATA_IMPORT_INITIALIZE, 'Import_register_JSON', register_handlers, {}, 75)

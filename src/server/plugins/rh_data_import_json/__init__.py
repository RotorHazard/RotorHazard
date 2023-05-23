'''JSON data importer'''

import logging
import json
import RHUtils
import Database
from data_import import DataImporter

logger = logging.getLogger(__name__)

def registerHandlers(args):
    if 'registerFn' in args:
        for importer in discover():
            args['registerFn'](importer)

def initialize(**kwargs):
    if 'Events' in kwargs:
        kwargs['Events'].on('Import_Initialize', 'Import_register_JSON', registerHandlers, {}, 75)

def import_json(racecontext, source_json, _args):
    rd = racecontext.rhdata
    
    if not source_json:
        return False

    try:
        data = json.loads(source_json)
    except Exception as ex:
        logger.error("Unable to import file: {}".format(str(ex)))
        # TODO: return error information
        return False

    db_pilots = rd.get_pilots()

    for input_pilot in data["Pilot"]:
        db_pilot_match = None
        for db_pilot in db_pilots:
            if db_pilot.callsign == input_pilot["callsign"]:
                db_pilot_match = db_pilot
                break

        if db_pilot_match:
            input_pilot["pilot_id"] = db_pilot_match.id
            rd.alter_pilot(input_pilot)
        else:
            rd.add_pilot(input_pilot)

def discover(*_args, **_kwargs):
    # returns array of exporters with default arguments, fields
    return [
        DataImporter(
            'json',
            'RotorHazard 4.0 JSON',
            import_json,
            None,
            None
        ),
    ]

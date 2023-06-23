''' Class ranking method: Best X rounds '''

import logging
import csv
from eventmanager import Evt
from Results import RacePointsMethod
from RHUI import UIField, UIFieldType, UIFieldSelectOption

logger = logging.getLogger(__name__)

def registerHandlers(args):
    if 'registerFn' in args:
        for method in discover():
            args['registerFn'](method)

def initialize(**kwargs):
    if 'Events' in kwargs:
        kwargs['Events'].on(Evt.POINTS_INITIALIZE, 'points_register_byrank', registerHandlers, {}, 75, True)

def points_by_position(_rhapi, leaderboard, args):
    try:
        points_list = [int(x.strip()) for x in args['points_list'].split(',')]
    except:
        logger.info("Unable to parse points list string")
        return leaderboard

    lb = leaderboard[leaderboard['meta']['primary_leaderboard']]

    for idx, line in enumerate(lb):
        if len(points_list) > idx:
            line['points'] = points_list[idx]

    return leaderboard


def discover(*_args, **_kwargs):
    # returns array of methods with default arguments
    return [
        RacePointsMethod(
            'position_basic',
            'Position',
            points_by_position,
            None,
            [
                UIField('points_list', "Points (CSV)", UIFieldType.TEXT, placeholder="10,6,3,1"),
            ]
        )
    ]

''' Class ranking method: Best X rounds '''

import logging
import csv
from Results import RacePointsMethod

logger = logging.getLogger(__name__)

def registerHandlers(args):
    if 'registerFn' in args:
        for method in discover():
            args['registerFn'](method)

def __(arg): # Replaced with outer language.__ during initialize()
    return arg

def initialize(**kwargs):
    if 'Events' in kwargs:
        kwargs['Events'].on('RacePoints_Initialize', 'points_register_byrank', registerHandlers, {}, 75, True)
    if '__' in kwargs:
        __ = kwargs['__']

def points_by_position(racecontext, leaderboard, args):
    try:
        points_list = [int(x.strip()) for x in args['points_list'].split(',')]
    except:
        logger.info("Unable to parse points list string")
        return None

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
            {
            },
            [
                {
                    'id': 'points_list',
                    'label': "Points (CSV)",
                    'placeholder': '10,6,3,1',
                    'fieldType': 'text',
                },
            ]
        )
    ]

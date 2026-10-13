'''Split timers: points on the course where a pass is recorded as a split of the pilot's lap'''

import logging

logger = logging.getLogger(__name__)

class SplitTimer:
    '''A split timer, from a secondary timer or a plugin. Its passes are recorded by
    RHRace.record_split(). 'settings' takes the split items of a secondary timer's
    config: 'distance', 'callout', 'toneDuration', 'toneFrequency', 'toneVolume',
    'toneType' and 'event' (see doc/Cluster.md).'''

    TIME_CALLOUT = "time"
    SPEED_CALLOUT = "speed"
    BOTH_CALLOUT = "both"
    NAME_ONLY_CALLOUT = "nameOnly"
    NONE_CALLOUT = "none"

    def __init__(self, split_id, settings=None, is_available=None):
        self.split_id = split_id
        self.settings = settings or {}
        self.distance = float(self.settings.get('distance', 0.0)) * 1000.0
        # timestamps of passes on the split timer before this one, by node, for speed-only records
        self.prev_pass_stamps = {}
        # whether the race page shows this timer's splits
        self.is_available = is_available or (lambda: True)
        calloutStr = self.settings.get('callout')
        if calloutStr is not None:
            calloutStr = calloutStr.lower()
        if calloutStr == SplitTimer.TIME_CALLOUT:
            self.timeCalloutFlag = True
            self.speedCalloutFlag = False
            self.nameCalloutFlag = True
        elif calloutStr == SplitTimer.SPEED_CALLOUT:
            self.timeCalloutFlag = False
            self.speedCalloutFlag = True
            self.nameCalloutFlag = True
        elif calloutStr == SplitTimer.BOTH_CALLOUT:
            self.timeCalloutFlag = True
            self.speedCalloutFlag = True
            self.nameCalloutFlag = True
        elif calloutStr == SplitTimer.NAME_ONLY_CALLOUT:
            self.timeCalloutFlag = False
            self.speedCalloutFlag = False
            self.nameCalloutFlag = True
        elif calloutStr == SplitTimer.NONE_CALLOUT:
            self.timeCalloutFlag = False
            self.speedCalloutFlag = False
            self.nameCalloutFlag = False
        else:
            if self.distance > 0.0:  # if 'distance' specified then default to calling out speed only
                self.timeCalloutFlag = False
                self.speedCalloutFlag = True
                self.nameCalloutFlag = True
            else:
                self.timeCalloutFlag = True
                self.speedCalloutFlag = False
                self.nameCalloutFlag = True
            if calloutStr is not None:
                logger.warning("Invalid 'callout' value in split timer config: {}".format(calloutStr))

def add_split_timer(split_timers, timer):
    '''Adds a split timer to 'split_timers' (by split number) unless its number is taken.
    Returns True if added.'''
    if timer.split_id in split_timers:
        logger.warning("Split timer {} not added: split number already in use".format(timer.split_id+1))
        return False
    split_timers[timer.split_id] = timer
    return True

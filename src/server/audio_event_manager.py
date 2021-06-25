import copy
import subprocess
import logging
from .eventmanager import Evt
from .RHRace import StagingTones, StartBehavior
from . import RHUtils

logger = logging.getLogger(__name__)


class AudioEventManager:

    def __init__(self, eventmanager, data, race, config):
        self.Events = eventmanager
        self.RHData = data
        self.RACE = race
        self.config = config
        self.proc = None

    def install_default_effects(self):
        if 'PLAYER' in self.config:
            self.addEvent(Evt.RACE_STAGE, stage_beep)
            self.addEvent(Evt.RACE_START_COUNTDOWN, countdown_beeps)
            self.addEvent(Evt.RACE_START, start_beep)
        if 'TTS' in self.config:
            self.addEvent(Evt.RACE_LAP_RECORDED, say_lap_time)

    def addEvent(self, event, effectFunc):
        self.Events.on(event, 'Audio', self.create_handler(effectFunc))

    def create_handler(self, func):
        def _handler(args):
            args['RHData'] = self.RHData
            args['RACE'] = self.RACE
            args['play'] = self.play
            args['say'] = self.say
            func(**args)

        return _handler

    def play(self, audio_file):
        if self.proc:
            self.proc.wait()
        args = copy.copy(self.config['PLAYER'])
        args.append(audio_file)
        self.proc = subprocess.Popen(args)

    def say(self, text):
        if self.proc:
            self.proc.wait()
        args = copy.copy(self.config['TTS'])
        args.append(text)
        self.proc = subprocess.Popen(args)


def stage_beep(RACE, play, **kwargs):
    if (RACE.format.staging_tones == StagingTones.TONES_ONE):
        play('server/static/audio/stage.wav')


def countdown_beeps(time_remaining, countdown_time, RACE, play, say, **kwargs):
    if (RACE.format.staging_tones == StagingTones.TONES_3_2_1 and time_remaining <= 3) \
        or (RACE.format.staging_tones == StagingTones.TONES_ALL):
        play('server/static/audio/stage.wav')
    elif time_remaining == 30 or time_remaining == 20 or time_remaining == 10:
        say("Starting in {} seconds".format(time_remaining))


def start_beep(play, **kwargs):
    play('server/static/audio/buzzer.wav')


def say_lap_time(node_index, lap, RHData, RACE, say, **kwargs):
    lap_num = lap['lap_number']
    if lap_num > 0 or RACE.format.start_behavior == StartBehavior.FIRST_LAP:
        pilot_id = RHData.get_pilot_from_heatNode(RACE.current_heat, node_index)
        pilot = RHData.get_pilot(pilot_id)
        phonetic_time = RHUtils.phonetictime_format(lap['lap_time'], RHData.get_option('timeFormatPhonetic'))
        say("{}, lap {}, {}".format(pilot.phonetic if pilot.phonetic else pilot.callsign, lap_num, phonetic_time))

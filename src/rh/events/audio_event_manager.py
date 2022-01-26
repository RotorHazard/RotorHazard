import copy
import subprocess
import logging
from rh.events.eventmanager import Evt
from rh.app.RHRace import RaceMode, StagingTones, StartBehavior
from rh.util import RHUtils

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
            self.addEvent(Evt.RACE_STAGE, play_stage_beep)
            self.addEvent(Evt.RACE_START_COUNTDOWN, play_start_countdown_beeps)
            self.addEvent(Evt.RACE_START, play_start_beep)
            self.addEvent(Evt.RACE_FIRST_PASS, play_first_pass_beep)
            self.addEvent(Evt.CROSSING_ENTER, play_crossing_enter_beep)
            self.addEvent(Evt.CROSSING_EXIT, play_crossing_exit_beep)
        if 'TTS' in self.config:
            self.addEvent(Evt.RACE_START_COUNTDOWN, say_start_countdown)
            self.addEvent(Evt.RACE_TICK, say_race_times)
            self.addEvent(Evt.RACE_LAP_RECORDED, say_lap_time)
            self.addEvent(Evt.RACE_FINISH, say_race_complete)

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
        if self.config['PLAYER']:
            args = copy.copy(self.config['PLAYER'])
            args.append(audio_file)
            self.proc = subprocess.Popen(args)

    def say(self, text):
        if self.proc:
            self.proc.wait()
        if self.config['TTS']:
            args = copy.copy(self.config['TTS'])
            args.append(text)
            self.proc = subprocess.Popen(args)


def play_stage_beep(RACE, play, **kwargs):
    if (RACE.format.staging_tones == StagingTones.TONES_ONE):
        play('server/static/audio/stage.wav')


def play_start_countdown_beeps(time_remaining, countdown_time, RACE, play, **kwargs):
    if (RACE.format.staging_tones == StagingTones.TONES_3_2_1 and time_remaining <= 3) \
        or (RACE.format.staging_tones == StagingTones.TONES_ALL):
        play('server/static/audio/stage.wav')


def say_start_countdown(time_remaining, countdown_time, RACE, say, **kwargs):
    if time_remaining == 30 or time_remaining == 20 or time_remaining == 10:
        say("Starting in {} seconds".format(time_remaining))


def play_start_beep(play, **kwargs):
    play('server/static/audio/buzzer.wav')


def play_first_pass_beep(play, **kwargs):
    play('server/static/audio/beep.wav')


def play_crossing_enter_beep(play, **kwargs):
    play('server/static/audio/enter.wav')


def play_crossing_exit_beep(play, **kwargs):
    play('server/static/audio/exit.wav')


def say_race_times(timer_sec, RACE, say, **kwargs):
    race_format = RACE.format
    if race_format.race_mode == RaceMode.FIXED_TIME:
        remaining = race_format.race_time_sec - timer_sec
        if remaining == 60:
            say("60 seconds")
        elif remaining == 30:
            say("30 seconds")
        elif remaining == 10:
            say("10 seconds")
        elif remaining == 0 and race_format.lap_grace_sec:
            say("Pilots, finish your lap");


def say_lap_time(node_index, lap, RHData, RACE, say, **kwargs):
    lap_num = lap['lap_number']
    race_format = RACE.format
    if lap_num > 0 or race_format.start_behavior == StartBehavior.FIRST_LAP:
        pilot = RACE.node_pilots[node_index]
        phonetic_time = RHUtils.phonetictime_format(lap['lap_time'], RHData.get_option('timeFormatPhonetic'))
        lap_time_stamp = lap['lap_time_stamp']
        msg = "{}".format(pilot.phonetic if pilot.phonetic else pilot.callsign)
        if race_format.lap_grace_sec and lap_time_stamp > race_format.race_time_sec*1000 and lap_time_stamp <= (race_format.race_time_sec + race_format.lap_grace_sec)*1000:
            msg += " done"
        msg += ", lap {}, {}".format(lap_num, phonetic_time)
        say(msg)


def say_race_complete(say, **kwargs):
    say("The race has finished")

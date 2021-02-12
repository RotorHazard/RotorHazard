'''
Database module
'''

import RHUtils
from flask_sqlalchemy import SQLAlchemy

DB = SQLAlchemy()

#
# Database Models
#
# pilot 1-N node
# node 1-N lap
# lap 1-N splits
# heat 1-N node
# round 1-N heat

class Pilot(DB.Model):
    __tablename__ = 'pilot'
    id = DB.Column(DB.Integer, primary_key=True)
    callsign = DB.Column(DB.String(80), nullable=False)
    team = DB.Column(DB.String(80), nullable=False, default=RHUtils.DEF_TEAM_NAME)
    phonetic = DB.Column(DB.String(80), nullable=False)
    name = DB.Column(DB.String(120), nullable=False)

    def __repr__(self):
        return '<Pilot %r>' % self.id

class Heat(DB.Model):
    __tablename__ = 'heat'
    id = DB.Column(DB.Integer, primary_key=True)
    note = DB.Column(DB.String(80), nullable=True)
    class_id = DB.Column(DB.Integer, DB.ForeignKey("race_class.id"), nullable=False)
    results = DB.Column(DB.PickleType, nullable=True)
    cacheStatus = DB.Column(DB.Integer, nullable=False)

    def __repr__(self):
        return '<Heat %r>' % self.id

class HeatNode(DB.Model):
    __tablename__ = 'heat_node'
    __table_args__ = (
        DB.UniqueConstraint('heat_id', 'node_index'),
    )
    id = DB.Column(DB.Integer, primary_key=True)
    heat_id = DB.Column(DB.Integer, DB.ForeignKey("heat.id"), nullable=False)
    node_index = DB.Column(DB.Integer, nullable=False)
    pilot_id = DB.Column(DB.Integer, DB.ForeignKey("pilot.id"), nullable=False)

    def __repr__(self):
        return '<HeatNode %r>' % self.id

class RaceClass(DB.Model):
    __tablename__ = 'race_class'
    id = DB.Column(DB.Integer, primary_key=True)
    name = DB.Column(DB.String(80), nullable=True)
    description = DB.Column(DB.String(256), nullable=True)
    format_id = DB.Column(DB.Integer, DB.ForeignKey("race_format.id"), nullable=False)
    results = DB.Column(DB.PickleType, nullable=True)
    cacheStatus = DB.Column(DB.Integer, nullable=False)

    def __repr__(self):
        return '<RaceClass %r>' % self.id

class LapSplit(DB.Model):
    __tablename__ = 'lap_split'
    __table_args__ = (
        DB.UniqueConstraint('node_index', 'lap_id', 'split_id'),
    )
    id = DB.Column(DB.Integer, primary_key=True)
    node_index = DB.Column(DB.Integer, nullable=False)
    pilot_id = DB.Column(DB.Integer, DB.ForeignKey("pilot.id"), nullable=False)
    lap_id = DB.Column(DB.Integer, nullable=False)
    split_id = DB.Column(DB.Integer, nullable=False)
    split_time_stamp = DB.Column(DB.Integer, nullable=False)
    split_time = DB.Column(DB.Integer, nullable=False)
    split_time_formatted = DB.Column(DB.Integer, nullable=False)
    split_speed = DB.Column(DB.Float, nullable=True)

    def __repr__(self):
        return '<LapSplit %r>' % self.pilot_id

class SavedRaceMeta(DB.Model):
    __tablename__ = 'saved_race_meta'
    __table_args__ = (
        DB.UniqueConstraint('round_id', 'heat_id'),
    )
    id = DB.Column(DB.Integer, primary_key=True)
    round_id = DB.Column(DB.Integer, nullable=False)
    heat_id = DB.Column(DB.Integer, DB.ForeignKey("heat.id"), nullable=False)
    class_id = DB.Column(DB.Integer, DB.ForeignKey("race_class.id"), nullable=False)
    format_id = DB.Column(DB.Integer, DB.ForeignKey("race_format.id"), nullable=False)
    start_time = DB.Column(DB.Integer, nullable=False) # internal monotonic time
    start_time_formatted = DB.Column(DB.String, nullable=False) # local human-readable time
    results = DB.Column(DB.PickleType, nullable=True)
    cacheStatus = DB.Column(DB.Integer, nullable=False)

    def __repr__(self):
        return '<SavedRaceMeta %r>' % self.id

class SavedPilotRace(DB.Model):
    __tablename__ = 'saved_pilot_race'
    __table_args__ = (
        DB.UniqueConstraint('race_id', 'node_index'),
    )
    id = DB.Column(DB.Integer, primary_key=True)
    race_id = DB.Column(DB.Integer, DB.ForeignKey("saved_race_meta.id"), nullable=False)
    node_index = DB.Column(DB.Integer, nullable=False)
    pilot_id = DB.Column(DB.Integer, DB.ForeignKey("pilot.id"), nullable=False)
    history_values = DB.Column(DB.String, nullable=True)
    history_times = DB.Column(DB.String, nullable=True)
    penalty_time = DB.Column(DB.Integer, nullable=False)
    penalty_desc = DB.Column(DB.String, nullable=True)
    enter_at = DB.Column(DB.Integer, nullable=False)
    exit_at = DB.Column(DB.Integer, nullable=False)

    def __repr__(self):
        return '<SavedPilotRace %r>' % self.id

class SavedRaceLap(DB.Model):
    __tablename__ = 'saved_race_lap'
    id = DB.Column(DB.Integer, primary_key=True)
    race_id = DB.Column(DB.Integer, DB.ForeignKey("saved_race_meta.id"), nullable=False)
    pilotrace_id = DB.Column(DB.Integer, DB.ForeignKey("saved_pilot_race.id"), nullable=False)
    node_index = DB.Column(DB.Integer, nullable=False)
    pilot_id = DB.Column(DB.Integer, DB.ForeignKey("pilot.id"), nullable=False)
    lap_time_stamp = DB.Column(DB.Integer, nullable=False)
    lap_time = DB.Column(DB.Integer, nullable=False)
    lap_time_formatted = DB.Column(DB.String, nullable=False)
    source = DB.Column(DB.Integer, nullable=False)
    deleted = DB.Column(DB.Boolean, nullable=False)

    def __repr__(self):
        return '<SavedRaceLap %r>' % self.id

class LapSource:
    REALTIME = 0
    MANUAL = 1
    RECALC = 2
    AUTOMATIC = 3

class Profiles(DB.Model):
    __tablename__ = 'profiles'
    id = DB.Column(DB.Integer, primary_key=True)
    name = DB.Column(DB.String(80), nullable=False)
    description = DB.Column(DB.String(256), nullable=True)
    frequencies = DB.Column(DB.String(80), nullable=False)
    enter_ats = DB.Column(DB.String(80), nullable=True)
    exit_ats = DB.Column(DB.String(80), nullable=True)
    f_ratio = DB.Column(DB.Integer, nullable=True)

class RaceFormat(DB.Model):
    __tablename__ = 'race_format'
    id = DB.Column(DB.Integer, primary_key=True)
    name = DB.Column(DB.String(80), nullable=False)
    race_mode = DB.Column(DB.Integer, nullable=False)
    race_time_sec = DB.Column(DB.Integer, nullable=False)
    start_delay_min = DB.Column(DB.Integer, nullable=False)
    start_delay_max = DB.Column(DB.Integer, nullable=False)
    staging_tones = DB.Column(DB.Integer, nullable=False)
    number_laps_win = DB.Column(DB.Integer, nullable=False)
    win_condition = DB.Column(DB.Integer, nullable=False)
    team_racing_mode = DB.Column(DB.Boolean, nullable=False)
    start_behavior = DB.Column(DB.Integer, nullable=False)

class GlobalSettings(DB.Model):
    __tablename__ = 'global_settings'
    id = DB.Column(DB.Integer, primary_key=True)
    option_name = DB.Column(DB.String(40), nullable=False)
    option_value = DB.Column(DB.String, nullable=False)


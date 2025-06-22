'''
Database module
'''

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base
import RHUtils
import logging
logger = logging.getLogger(__name__)

DB_engine = None
DB_session = None
DB_URI = None

Base = declarative_base()
DB = sqlalchemy

DB_POOL_SIZE=10
DB_MAX_OVERFLOW=100

#pylint: disable=no-member

# Language placeholder (Overwritten after module init)
def __(*args):
    return args

# Context placeholder (Overwritten after module init)
racecontext = None

#
# Database Models
#
# pilot 1-N node
# node 1-N lap
# lap 1-N splits
# heat 1-N node
# round 1-N heat

class Pilot(Base):
    __tablename__ = 'pilot'
    id = DB.Column(DB.Integer, primary_key=True)
    callsign = DB.Column(DB.String(80), nullable=False)
    team = DB.Column(DB.String(80), nullable=False, default=RHUtils.DEF_TEAM_NAME)
    phonetic = DB.Column(DB.String(80), nullable=False)
    name = DB.Column(DB.String(120), nullable=False)
    color = DB.Column(DB.String(7), nullable=True)
    used_frequencies = DB.Column(DB.String, nullable=True)
    active = DB.Column(DB.Boolean, nullable=False, default=True)

    @property
    def display_callsign(self):
        if self.callsign:
            return self.callsign
        if self.name:
            return self.name
        return "{} {}".format(__('Pilot'), id)

    @property
    def display_name(self):
        if self.name:
            return self.name
        if self.callsign:
            return self.callsign
        return "{} {}".format(__('Pilot'), id)

    @property
    def spoken_callsign(self):
        if self.phonetic:
            return self.phonetic
        if self.callsign:
            return self.callsign
        if self.name:
            return self.name
        return "{} {}".format(__('Pilot'), id)

    def __repr__(self):
        return '<Pilot %r>' % self.id

class PilotAttribute(Base):
    __tablename__ = 'pilot_attribute'
    __table_args__ = (
        DB.UniqueConstraint('id', 'name'),
    )
    id = DB.Column(DB.Integer, DB.ForeignKey("pilot.id"), nullable=False, primary_key=True)
    name = DB.Column(DB.String(80), nullable=False, primary_key=True)
    value = DB.Column(DB.String(), nullable=True)

class Heat(Base):
    __tablename__ = 'heat'
    id = DB.Column(DB.Integer, primary_key=True)
    name = DB.Column('note', DB.String(80), nullable=True)
    auto_name = DB.Column(DB.String(80), nullable=True)
    class_id = DB.Column(DB.Integer, DB.ForeignKey("race_class.id"), nullable=False)
    results = DB.Column(DB.PickleType, nullable=True)
    _cache_status = DB.Column('cacheStatus', DB.String(16), nullable=False)
    order = DB.Column(DB.Integer, nullable=True)
    status = DB.Column(DB.Integer, nullable=False)
    auto_frequency = DB.Column(DB.Boolean, nullable=False)
    group_id = DB.Column(DB.Integer, nullable=False)
    active = DB.Column(DB.Boolean, nullable=False, default=True)
    coop_best_time = DB.Column(DB.Float, nullable=True, default=0.0)  # best time achieved in co-op racing mode (seconds)
    coop_num_laps = DB.Column(DB.Integer, nullable=True, default=0)   # best # of laps in co-op racing mode

    # DEPRECATED: compatibility for 'note' property / renamed to 'name'
    @property
    def note(self):
        logger.warning("Use of deprecated note attribute, use 'name'", stack_info=True)
        return self.name

    @note.setter
    def note(self, value):
        logger.warning("Use of deprecated note attribute, use 'name'", stack_info=True)
        self.name = value

    # DEPRECATED: compatibility for 'cacheStatus' property / renamed to '_cache_status'
    @property
    def cacheStatus(self):
        logger.warning("Use of deprecated cacheStatus attribute, use '_cache_status'", stack_info=True)
        return self._cache_status

    @cacheStatus.setter
    def cacheStatus(self, value):
        logger.warning("Use of deprecated cacheStatus attribute, use '_cache_status'", stack_info=True)
        self._cache_status = value

    @property
    def display_name(self):
        output = ''
        if self.class_id:
            # get class, check class.group_id
            race_class = racecontext.rhdata.get_raceClass(self.class_id)
            if self.class_id and race_class.round_type == RoundType.GROUPED:
                output = f"{__('Round')} {self.group_id + 1} / "

        if self.name:
            output += self.name
        elif self.auto_name:
            output += self.auto_name
        else:
            output = f"{__('Heat')} {str(self.id)}"

        return output

    @property
    def display_name_short(self):
        output = ''
        if self.name:
            output += self.name
        elif self.auto_name:
            output += self.auto_name
        else:
            output = f"{__('Heat')} {str(self.id)}"

        return output

    def __repr__(self):
        return '<Heat %r>' % self.id

class HeatStatus:
    PLANNED = 0
    PROJECTED = 1
    CONFIRMED = 2

class HeatAttribute(Base):
    __tablename__ = 'heat_attribute'
    __table_args__ = (
        DB.UniqueConstraint('id', 'name'),
    )
    id = DB.Column(DB.Integer, DB.ForeignKey("heat.id"), nullable=False, primary_key=True)
    name = DB.Column(DB.String(80), nullable=False, primary_key=True)
    value = DB.Column(DB.String(), nullable=True)

class HeatNode(Base):
    __tablename__ = 'heat_node'
    __table_args__ = (
        DB.UniqueConstraint('heat_id', 'node_index'),
    )
    id = DB.Column(DB.Integer, primary_key=True)
    heat_id = DB.Column(DB.Integer, DB.ForeignKey("heat.id"), nullable=False)
    node_index = DB.Column(DB.Integer, nullable=True)
    pilot_id = DB.Column(DB.Integer, DB.ForeignKey("pilot.id"), nullable=False)
    color = DB.Column(DB.String(6), nullable=True)
    method = DB.Column(DB.Integer, nullable=False)
    seed_rank = DB.Column(DB.Integer, nullable=True)
    seed_id = DB.Column(DB.Integer, nullable=True)

    def __repr__(self):
        return '<HeatNode %r>' % self.id

class ProgramMethod:
    NONE = -1
    ASSIGN = 0
    HEAT_RESULT = 1
    CLASS_RESULT = 2

class RaceClass(Base):
    __tablename__ = 'race_class'
    id = DB.Column(DB.Integer, primary_key=True)
    name = DB.Column(DB.String(80), nullable=True)
    description = DB.Column(DB.String(256), nullable=True)
    format_id = DB.Column(DB.Integer, DB.ForeignKey("race_format.id"), nullable=False)
    win_condition = DB.Column(DB.String, nullable=False)
    results = DB.Column(DB.PickleType, nullable=True)
    _cache_status = DB.Column('cacheStatus', DB.String(16), nullable=False)
    ranking = DB.Column(DB.PickleType, nullable=True)
    rank_settings = DB.Column(DB.String(), nullable=True)
    _rank_status = DB.Column('rankStatus', DB.String(16), nullable=False)
    rounds = DB.Column(DB.Integer, nullable=False)
    heat_advance_type = DB.Column('heatAdvanceType', DB.Integer, nullable=False)
    round_type = DB.Column('roundType', DB.Integer, nullable=False)
    order = DB.Column(DB.Integer, nullable=True)
    active = DB.Column(DB.Boolean, nullable=False, default=True)

    # DEPRECATED: compatibility for 'cacheStatus' property / renamed to '_cache_status'
    @property
    def cacheStatus(self):
        logger.warning("Use of deprecated cacheStatus attribute, use '_cache_status'", stack_info=True)
        return self._cache_status

    @cacheStatus.setter
    def cacheStatus(self, value):
        logger.warning("Use of deprecated cacheStatus attribute, use '_cache_status'", stack_info=True)
        self._cache_status = value

    # DEPRECATED: compatibility for 'rankStatus' property / renamed to '_rank_status'
    @property
    def rankStatus(self):
        logger.warning("Use of deprecated rankStatus attribute, use '_rank_status'", stack_info=True)
        return self._rank_status

    @rankStatus.setter
    def rankStatus(self, value):
        logger.warning("Use of deprecated rankStatus attribute, use '_rank_status'", stack_info=True)
        self._rank_status = value

    # DEPRECATED: compatibility for 'heatAdvanceType' property / renamed to 'heat_advance_type'
    @property
    def heatAdvanceType(self):
        logger.warning("Use of deprecated heatAdvanceType attribute, use 'heat_advance_type'", stack_info=True)
        return self.heat_advance_type

    @heatAdvanceType.setter
    def heatAdvanceType(self, value):
        logger.warning("Use of deprecated heatAdvanceType attribute, use 'heat_advance_type'", stack_info=True)
        self.heat_advance_type = value

    @property
    def display_name(self):
        if self.name:
            return self.name
        return "{} {}".format(__('Class'), str(self.id))

    def __repr__(self):
        return '<RaceClass %r>' % self.id

class HeatAdvanceType:
    NONE = 0
    NEXT_HEAT = 1
    NEXT_ROUND = 2

class RoundType:
    RACES_PER_HEAT = 0
    GROUPED = 1

class RaceClassAttribute(Base):
    __tablename__ = 'race_class_attribute'
    __table_args__ = (
        DB.UniqueConstraint('id', 'name'),
    )
    id = DB.Column(DB.Integer, DB.ForeignKey("race_class.id"), nullable=False, primary_key=True)
    name = DB.Column(DB.String(80), nullable=False, primary_key=True)
    value = DB.Column(DB.String(), nullable=True)

class LapSplit(Base):
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

class SavedRaceMeta(Base):
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
    _cache_status = DB.Column('cacheStatus', DB.String(16), nullable=False)

    # DEPRECATED: compatibility for 'cacheStatus' property / renamed to '_cache_status'
    @property
    def cacheStatus(self):
        logger.warning("Use of deprecated cacheStatus attribute, use '_cache_status'", stack_info=True)
        return self._cache_status

    @cacheStatus.setter
    def cacheStatus(self, value):
        logger.warning("Use of deprecated cacheStatus attribute, use '_cache_status'", stack_info=True)
        self._cache_status = value

    def __repr__(self):
        return '<SavedRaceMeta %r>' % self.id

class SavedRaceMetaAttribute(Base):
    __tablename__ = 'saved_race_meta_attribute'
    __table_args__ = (
        DB.UniqueConstraint('id', 'name'),
    )
    id = DB.Column(DB.Integer, DB.ForeignKey("saved_race_meta.id"), nullable=False, primary_key=True)
    name = DB.Column(DB.String(80), nullable=False, primary_key=True)
    value = DB.Column(DB.String(), nullable=True)

class SavedPilotRace(Base):
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
    frequency = DB.Column(DB.Integer, nullable=True)

    def __repr__(self):
        return '<SavedPilotRace %r>' % self.id

class SavedRaceLap(Base):
    __tablename__ = 'saved_race_lap'
    id = DB.Column(DB.Integer, primary_key=True)
    race_id = DB.Column(DB.Integer, DB.ForeignKey("saved_race_meta.id"), nullable=False)
    pilotrace_id = DB.Column(DB.Integer, DB.ForeignKey("saved_pilot_race.id"), nullable=False)
    node_index = DB.Column(DB.Integer, nullable=False)
    pilot_id = DB.Column(DB.Integer, DB.ForeignKey("pilot.id"), nullable=False)
    lap_time_stamp = DB.Column(DB.Float, nullable=False)
    lap_time = DB.Column(DB.Float, nullable=False)
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
    API = 4

class Profiles(Base):
    __tablename__ = 'profiles'
    id = DB.Column(DB.Integer, primary_key=True)
    name = DB.Column(DB.String(80), nullable=False)
    description = DB.Column(DB.String(256), nullable=True)
    frequencies = DB.Column(DB.String(80), nullable=False)
    enter_ats = DB.Column(DB.String(80), nullable=True)
    exit_ats = DB.Column(DB.String(80), nullable=True)
    f_ratio = DB.Column(DB.Integer, nullable=True)

class RaceFormat(Base):
    __tablename__ = 'race_format'
    id = DB.Column(DB.Integer, primary_key=True)
    name = DB.Column(DB.String(80), nullable=False)
    unlimited_time = DB.Column('race_mode', DB.Integer, nullable=False)
    race_time_sec = DB.Column(DB.Integer, nullable=False)
    lap_grace_sec = DB.Column(DB.Integer, nullable=False, default=-1)
    staging_fixed_tones = DB.Column(DB.Integer, nullable=False)
    start_delay_min_ms = DB.Column(DB.Integer, nullable=False)
    start_delay_max_ms = DB.Column(DB.Integer, nullable=False)
    staging_delay_tones = DB.Column('staging_tones', DB.Integer, nullable=False)
    number_laps_win = DB.Column(DB.Integer, nullable=False)
    win_condition = DB.Column(DB.Integer, nullable=False)
    team_racing_mode = DB.Column(DB.Integer, nullable=False)
    start_behavior = DB.Column(DB.Integer, nullable=False)
    points_method = DB.Column(DB.String, nullable=True)

    # DEPRECATED: compatibility for 'race_mode' property / renamed to 'unlimited_time'
    @property
    def race_mode(self):
        logger.warning("Use of deprecated race_mode attribute, use 'unlimited_time'", stack_info=True)
        return self.unlimited_time

    @race_mode.setter
    def race_mode(self, value):
        logger.warning("Use of deprecated race_mode attribute, use 'unlimited_time'", stack_info=True)
        self.unlimited_time = value

    # DEPRECATED: compatibility for 'staging_tones' property / renamed to 'staging_delay_tones'
    @property
    def staging_tones(self):
        logger.warning("Use of deprecated staging_tones attribute, use 'staging_delay_tones'", stack_info=True)
        return self.staging_delay_tones

    @staging_tones.setter
    def staging_tones(self, value):
        logger.warning("Use of deprecated staging_tones attribute, use 'staging_delay_tones'", stack_info=True)
        self.staging_delay_tones = value

class RaceFormatAttribute(Base):
    __tablename__ = 'race_format_attribute'
    __table_args__ = (
        DB.UniqueConstraint('id', 'name'),
    )
    id = DB.Column(DB.Integer, DB.ForeignKey("race_format.id"), nullable=False, primary_key=True)
    name = DB.Column(DB.String(80), nullable=False, primary_key=True)
    value = DB.Column(DB.String(), nullable=True)

    def __repr__(self):
        return '<RaceFormatAttribute %r %s>' % (self.id, self.name)

class GlobalSettings(Base):
    __tablename__ = 'global_settings'
    id = DB.Column(DB.Integer, primary_key=True)
    option_name = DB.Column(DB.String(40), nullable=False)
    option_value = DB.Column(DB.String, nullable=True)

    def __repr__(self):
        return '<GlobalSetting %r>' % self.id

def initialize(db_uri=None):
    close_database()
    global DB_URI
    if db_uri:
        DB_URI = db_uri
    global DB_engine
    DB_engine = create_engine(DB_URI, pool_size=DB_POOL_SIZE, max_overflow=DB_MAX_OVERFLOW)
    global DB_session
    DB_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, \
                                             bind=DB_engine, expire_on_commit=False))
    Base.query = DB_session.query_property()

def create_db_all():
    Base.metadata.create_all(bind=DB_engine)

def close_database():
    global DB_session
    if DB_session:
        DB_session.remove()
        DB_session = None
    global DB_engine
    if DB_engine:
        DB_engine.dispose()
        DB_engine = None

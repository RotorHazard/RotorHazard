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

#
# Database Models
#
# pilot 1-N node
# node 1-N lap
# lap 1-N splits
# heat 1-N node
# round 1-N heat

class Pilot(Base):
    """A pilot is an individual participant. In order to participate in races, pilots can be assigned to multiple heats.

    :cvar id: Internal identifier
    :vartype id: int
    :cvar callsign: Callsign
    :vartype callsign: str
    :cvar team: Team designation
    :vartype team: str
    :cvar phonetic: Phonetically-spelled callsign, used for text-to-speech
    :vartype phonetic: str
    :cvar color: Hex-encoded color
    :vartype color: str
    :cvar used_frequencies: Serialized list of frequencies this pilot has been assigned when starting a race, ordered by recency
    :vartype used_frequencies: str
    :cvar active: Not yet implemented
    :vartype active: bool

    The sentinel value RHUtils.PILOT_ID_NONE should be used when no pilot is defined.
    """
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
    """Pilot Attributes are simple storage variables which persist to the database and can be presented to users through frontend UI. Pilot Attribute values are unique to/stored individually for each pilot.

    :cvar id: ID of pilot to which this attribute is assigned
    :vartype id: int
    :cvar name: Name of attribute
    :vartype name: str
    :cvar value: Value of attribute
    :vartype value: str
    """
    __tablename__ = 'pilot_attribute'
    __table_args__ = (
        DB.UniqueConstraint('id', 'name'),
    )
    id = DB.Column(DB.Integer, DB.ForeignKey("pilot.id"), nullable=False, primary_key=True)
    name = DB.Column(DB.String(80), nullable=False, primary_key=True)
    value = DB.Column(DB.String(), nullable=True)

class Heat(Base):
    """Heats are collections of pilots upon which races are run. A heat may first be represented by a heat plan which defines methods for assigning pilots. The plan must be seeded into pilot assignments in order for a race to be run.

    :cvar id: Internal identifier
    :vartype id: int
    :cvar name: User-facing name
    :vartype name: str
    :cvar class_id: ID of associated race class
    :vartype class_id: int
    :cvar results: Internal use only; see below
    :vartype results: dict|None
    :cvar _cache_status: Internal use only
    :cvar order: ID of pilot to which this attribute is assigned
    :vartype order: int
    :cvar status: ID of pilot to which this attribute is assigned
    :vartype status: HeatStatus
    :cvar auto_frequency: ID of pilot to which this attribute is assigned
    :vartype auto_frequency: bool
    :cvar active: ID of pilot to which this attribute is assigned
    :vartype active: bool

    The sentinel value RHUtils.HEAT_ID_NONE should be used when no heat is defined.

    NOTE: Results should be accessed with the db.heat_results method and not by reading the results property directly. The results property is unreliable because results calulation is delayed to improve system performance. db.heat_results ensures the calculation is current, will return quickly from cache if possible, or will build it if necessary.
    """
    __tablename__ = 'heat'
    id = DB.Column(DB.Integer, primary_key=True)
    name = DB.Column('note', DB.String(80), nullable=True)
    class_id = DB.Column(DB.Integer, DB.ForeignKey("race_class.id"), nullable=False)
    results = DB.Column(DB.PickleType, nullable=True)
    _cache_status = DB.Column('cacheStatus', DB.String(16), nullable=False)
    order = DB.Column(DB.Integer, nullable=True)
    status = DB.Column(DB.Integer, nullable=False)
    auto_frequency = DB.Column(DB.Boolean, nullable=False)
    active = DB.Column(DB.Boolean, nullable=False, default=True)

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
        if self.name:
            return self.name
        return "{} {}".format(__('Heat'), str(self.id))

    def __repr__(self):
        return '<Heat %r>' % self.id

class HeatStatus():
    """_summary_

    :cvar PLANNED: _description_
    :cvar PROJECTED: _description_
    :cvar CONFIRMED: _description_
    """
    PLANNED = 0
    PROJECTED = 1
    CONFIRMED = 2

class HeatAttribute(Base):
    """Heat Attributes are simple storage variables which persist to the database. Heat Attribute values are unique to/stored individually for each heat.

    :cvar id: ID of heat to which this attribute is assigned
    :vartype id: int
    :cvar name: Name of attribute
    :vartype name: str
    :cvar value: Value of attribute
    :vartype value: str
    """
    __tablename__ = 'heat_attribute'
    __table_args__ = (
        DB.UniqueConstraint('id', 'name'),
    )
    id = DB.Column(DB.Integer, DB.ForeignKey("heat.id"), nullable=False, primary_key=True)
    name = DB.Column(DB.String(80), nullable=False, primary_key=True)
    value = DB.Column(DB.String(), nullable=True)

class HeatNode(Base):
    """Slots are data structures containing a pilot assignment or assignment method. Heats contain one or more Slots corresponding to pilots who may participate in the Heat. When a heat is calculated, the method is used to reserve a slot for a given pilot. Afterward, pilot contains the ID for which the space is reserved. A Slot assignment is only a reservation, it does not mean the pilot has raced regardless of heat status.

    :cvar id: Internal identifier
    :vartype id: int
    :cvar heat_id: ID of heat to which this slot is assigned
    :vartype heat_id: int
    :cvar node_index: slot number
    :vartype node_index: int
    :cvar pilot_id: ID of pilot assigned to this slot
    :vartype pilot_id: int|None
    :cvar color: hexadecimal color assigned to this slot
    :vartype color: str
    :cvar method: Method used to implement heat plan
    :vartype method: ProgramMethod
    :cvar seed_rank: Rank value used when implementing heat plan
    :vartype seed_rank: int
    :cvar seed_id: ID of heat or class used when implementing heat plan
    :vartype seed_id: int
    """
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
    """Defines the method used when a heat plan is converted to assignments

    :cvar NONE: No assignment made
    :cvar ASSIGN: Use pilot already defined in pilot_id
    :cvar HEAT_RESULT: Assign using seed_id as a heat designation
    :cvar CLASS_RESULT: Assign using seed_id as a race class designation
    """
    NONE = -1
    ASSIGN = 0
    HEAT_RESULT = 1
    CLASS_RESULT = 2

class HeatAdvanceType:
    """Defines how the UI will automatically advance heats after a race is finished."""

    NONE:int = 0
    """Do nothing"""
    NEXT_HEAT:int = 1
    """Advance heat; if all rounds run advance race class"""
    NEXT_ROUND:int = 2
    """Advance heat if rounds has been reached; advance race class after last heat in class"""

class RaceClass(Base):
    """Race classes are groups of related heats. Classes may be used by the race organizer in many different ways, such as splitting sport and pro pilots, practice/qualifying/mains, primary/consolation bracket, etc.

    The sentinel value RHUtils.CLASS_ID_NONE should be used when no race class is defined.

    NOTE: Results should be accessed with the db.raceclass_results method and not by reading the results property directly. The results property is unreliable because results calculation is delayed to improve system performance. db.raceclass_results ensures the calculation is current, will return quickly from cache if possible, or will build it if necessary.
    """
    __tablename__ = 'race_class'
    id:int = DB.Column(DB.Integer, primary_key=True)
    """Internal identifier"""
    name:str = DB.Column(DB.String(80), nullable=True)
    """User-facing name"""
    description:str = DB.Column(DB.String(256), nullable=True)
    """User-facing long description, accepts markdown"""
    format_id:int = DB.Column(DB.Integer, DB.ForeignKey("race_format.id"), nullable=False)
    """ID for class-wide required race format definition"""
    win_condition:str = DB.Column(DB.String, nullable=False)
    """Ranking algorithm"""
    results:dict|None = DB.Column(DB.PickleType, nullable=True)
    """Internal use only; see below"""
    _cache_status = DB.Column('cacheStatus', DB.String(16), nullable=False)
    """Internal use only"""
    ranking:dict|None = DB.Column(DB.PickleType, nullable=True)
    """Calculated race class ranking"""
    rank_settings:str = DB.Column(DB.String(), nullable=True)
    """JSON-serialized arguments for ranking algorithm"""
    _rank_status = DB.Column('rankStatus', DB.String(16), nullable=False)
    """Internal use only"""
    rounds:int = DB.Column(DB.Integer, nullable=False)
    """Number of expected/planned rounds each heat will be run"""
    heat_advance_type:HeatAdvanceType = DB.Column('heatAdvanceType', DB.Integer, nullable=False)
    """Method used for automatic heat advance"""
    order:int = DB.Column(DB.Integer, nullable=True)
    """Not yet implemented"""
    active:bool = DB.Column(DB.Boolean, nullable=False, default=True)
    """Not yet implemented"""

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

class RaceClassAttribute(Base):
    """Race Class Attributes are simple storage variables which persist to the database. Race Class Attribute values are unique to/stored individually for each race class."""
    __tablename__ = 'race_class_attribute'
    __table_args__ = (
        DB.UniqueConstraint('id', 'name'),
    )
    id:int = DB.Column(DB.Integer, DB.ForeignKey("race_class.id"), nullable=False, primary_key=True)
    """ID of race class to which this attribute is assigned"""
    name:str = DB.Column(DB.String(80), nullable=False, primary_key=True)
    """Name of attribute"""
    value:str = DB.Column(DB.String(), nullable=True)
    """Value of attribute"""

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
    """Race formats are profiles of properties used to define parameters of individual races. Every race has an assigned format. A race formats may be assigned to a race class, which forces RotorHazard to switch to that formatwhen running races within the class.

    :cvar id: Internal identifier
    :vartype id: int
    :cvar name: User-facing name
    :vartype name: str
    :cvar unlimited_time: True(1) if race clock counts up, False(0) if race clock counts down
    :vartype unlimited_time: int
    :cvar race_time_sec: Race clock duration in seconds, unused if unlimited_time is True(1)
    :vartype race_time_sec: int
    :cvar lap_grace_sec: Grace period duration in seconds, -1 for unlimited, unused if unlimited_time is True(1)
    :vartype lap_grace_sec: int
    :cvar staging_fixed_tones: Number of staging tones always played regardless of random delay
    :vartype staging_fixed_tones: int
    :cvar start_delay_min_ms: Minimum period for random phase of staging delay in milliseconds
    :vartype start_delay_min_ms: int
    :cvar start_delay_max_ms: Maximum duration of random phase of staging delay in milliseconds
    :vartype start_delay_max_ms: int
    :cvar staging_delay_tones: Whether to play staging tones each second during random delay phase
    :vartype staging_delay_tones: int
    :cvar number_laps_win: Number of laps used to declare race winner, if > 0
    :vartype number_laps_win: int
    :cvar win_condition: Condition used to determine race winner and race ranking
    :vartype win_condition: int
    :cvar team_racing_mode: Whether local simultaneous team racing mode will be used
    :vartype team_racing_mode: bool
    :cvar start_behavior: Handling of first crossing
    :vartype start_behavior: int
    :cvar points_method: JSON-serialized arguments for points algorithm
    :vartype points_method: str
    
    The sentinel value RHUtils.FORMAT_ID_NONE should be used when no race format is defined.

    The following values are valid for staging_delay_tones.

        0: None

        2: Each Second

    The following values are valid for win_condition.

        0: None

        1: Most Laps in Fastest Time

        2: First to X Laps

        3: Fastest Lap

        4: Fastest Consecutive Laps

        5: Most Laps Only

        6: Most Laps Only with Overtime

    The following values are valid for start_behavior.

        0: Hole Shot

        1: First Lap

        2: Staggered Start

    Notice: The race format specification is expected to be modified in future versions. Please consider this while developing plugins.

        The type for staging_delay_tones may change to boolean.

        The type for unlimited_time may change to boolean.

        The type for win_condition may change to a members of dedicated class or become string-based for extensibility.

        The type for start_behavior may change to a members of dedicated class.
    """
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
    team_racing_mode = DB.Column(DB.Boolean, nullable=False)
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

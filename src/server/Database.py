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

    The sentinel value RHUtils.PILOT_ID_NONE should be used when no pilot is defined."""
    __tablename__ = 'pilot'
    id:int = DB.Column(DB.Integer, primary_key=True)
    """Internal identifier"""
    callsign:str = DB.Column(DB.String(80), nullable=False)
    """Callsign"""
    team:str = DB.Column(DB.String(80), nullable=False, default=RHUtils.DEF_TEAM_NAME)
    """Team designation"""
    phonetic:str = DB.Column(DB.String(80), nullable=False)
    """Phonetically-spelled callsign, used for text-to-speech"""
    name:str = DB.Column(DB.String(120), nullable=False)
    """Pilot name"""
    color:str = DB.Column(DB.String(7), nullable=True)
    """Hex-encoded color"""
    used_frequencies:str = DB.Column(DB.String, nullable=True)
    """Serialized list of frequencies this pilot has been assigned when starting a race, ordered by recency"""
    active:bool = DB.Column(DB.Boolean, nullable=False, default=True)
    """Not yet implemented"""

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
    """Pilot Attributes are simple storage variables which persist to the database and can be presented to users through frontend UI. Pilot Attribute values are unique to/stored individually for each pilot."""
    __tablename__ = 'pilot_attribute'
    __table_args__ = (
        DB.UniqueConstraint('id', 'name'),
    )
    id:int = DB.Column(DB.Integer, DB.ForeignKey("pilot.id"), nullable=False, primary_key=True)
    """ID of pilot to which this attribute is assigned"""
    name:str = DB.Column(DB.String(80), nullable=False, primary_key=True)
    """Name of attribute"""
    value = DB.Column(DB.String(), nullable=True)
    """Value of attribute"""

class HeatStatus():
    """_summary_"""

    PLANNED = 0
    """_description_"""
    PROJECTED = 1
    """_description_"""
    CONFIRMED = 2
    """_description_"""

class Heat(Base):
    """Heats are collections of pilots upon which races are run. A heat may first be represented by a heat plan which defines methods for assigning pilots. The plan must be seeded into pilot assignments in order for a race to be run.

    The sentinel value RHUtils.HEAT_ID_NONE should be used when no heat is defined.

    NOTE: Results should be accessed with the db.heat_results method and not by reading the results property directly. The results property is unreliable because results calulation is delayed to improve system performance. db.heat_results ensures the calculation is current, will return quickly from cache if possible, or will build it if necessary.
    """
    __tablename__ = 'heat'
    id:int = DB.Column(DB.Integer, primary_key=True)
    """Internal identifier"""
    name:str = DB.Column('note', DB.String(80), nullable=True)
    """User-facing name"""
    class_id:int = DB.Column(DB.Integer, DB.ForeignKey("race_class.id"), nullable=False)
    """ID of associated race class"""
    results:dict|None = DB.Column(DB.PickleType, nullable=True)
    """Internal use only"""
    _cache_status = DB.Column('cacheStatus', DB.String(16), nullable=False)
    """Internal use only"""
    order:int = DB.Column(DB.Integer, nullable=True)
    """Not yet implemented"""
    status:HeatStatus = DB.Column(DB.Integer, nullable=False)
    """Current status of heat as :attr:`HeatStatus.PLANNED` or :attr:`HeatStatus.CONFIRMED`"""
    auto_frequency:bool = DB.Column(DB.Boolean, nullable=False)
    """True to assign pilot seats automatically, False for direct assignment"""
    active:bool = DB.Column(DB.Boolean, nullable=False, default=True)
    """Not yet implemented"""

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

class HeatAttribute(Base):
    """Heat Attributes are simple storage variables which persist to the database. Heat Attribute values are unique to/stored individually for each heat."""
    __tablename__ = 'heat_attribute'
    __table_args__ = (
        DB.UniqueConstraint('id', 'name'),
    )
    id:int = DB.Column(DB.Integer, DB.ForeignKey("heat.id"), nullable=False, primary_key=True)
    """ID of heat to which this attribute is assigned"""
    name:str = DB.Column(DB.String(80), nullable=False, primary_key=True)
    """Name of attribute"""
    value:str = DB.Column(DB.String(), nullable=True)
    """Value of attribute"""

class ProgramMethod:
    """Defines the method used when a heat plan is converted to assignments"""

    NONE = -1
    """No assignment made"""
    ASSIGN = 0
    """Use pilot already defined in pilot_id"""
    HEAT_RESULT = 1
    """Assign using seed_id as a heat designation"""
    CLASS_RESULT = 2
    """Assign using seed_id as a race class designation"""

class HeatNode(Base):
    """Slots are data structures containing a pilot assignment or assignment method. Heats contain one or more Slots corresponding to pilots who may participate in the Heat. When a heat is calculated, the method is used to reserve a slot for a given pilot. Afterward, pilot contains the ID for which the space is reserved. A Slot assignment is only a reservation, it does not mean the pilot has raced regardless of heat status."""
    __tablename__ = 'heat_node'
    __table_args__ = (
        DB.UniqueConstraint('heat_id', 'node_index'),
    )
    id:int = DB.Column(DB.Integer, primary_key=True)
    """Internal identifier"""
    heat_id:int = DB.Column(DB.Integer, DB.ForeignKey("heat.id"), nullable=False)
    """ID of heat to which this slot is assigned"""
    node_index:int = DB.Column(DB.Integer, nullable=True)
    """slot number"""
    pilot_id:int = DB.Column(DB.Integer, DB.ForeignKey("pilot.id"), nullable=False)
    """ID of pilot assigned to this slot"""
    color:str = DB.Column(DB.String(6), nullable=True)
    """hexadecimal color assigned to this slot"""
    method:ProgramMethod = DB.Column(DB.Integer, nullable=False)
    """Method used to implement heat plan"""
    seed_rank:int = DB.Column(DB.Integer, nullable=True)
    """Rank value used when implementing heat plan"""
    seed_id:int = DB.Column(DB.Integer, nullable=True)
    """ID of heat or class used when implementing heat plan"""

    def __repr__(self):
        return '<HeatNode %r>' % self.id

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
    """Saved races are sets of stored information about race history. The Saved race object stores results and metadata. For a complete picture of a saved race, it is necessary to fetch associated Pilot Runs and Laps.
    
    NOTE: Results should be accessed with the db.race_results method and not by reading the results property directly. The results property is unreliable because results calulation is delayed to improve system performance. db.race_results ensures the calculation is current, will return quickly from cache if possible, or will build it if necessary.
    """
    __tablename__ = 'saved_race_meta'
    __table_args__ = (
        DB.UniqueConstraint('round_id', 'heat_id'),
    )
    id:int = DB.Column(DB.Integer, primary_key=True)
    """Internal identifier"""
    round_id:int = DB.Column(DB.Integer, nullable=False)
    """Round Number"""
    heat_id:int = DB.Column(DB.Integer, DB.ForeignKey("heat.id"), nullable=False)
    """ID of the associated heat"""
    class_id:int = DB.Column(DB.Integer, DB.ForeignKey("race_class.id"), nullable=False)
    """ID of associated race class, or CLASS_ID_NONE"""
    format_id:int = DB.Column(DB.Integer, DB.ForeignKey("race_format.id"), nullable=False)
    """ID of associated race format"""
    start_time:int = DB.Column(DB.Integer, nullable=False) # internal monotonic time
    """Internal (monotonic) time value of race start"""
    start_time_formatted:str = DB.Column(DB.String, nullable=False) # local human-readable time
    """Human-readable time of race start"""
    results:dict|None = DB.Column(DB.PickleType, nullable=True)
    """Internal use only; see below"""
    _cache_status = DB.Column('cacheStatus', DB.String(16), nullable=False)
    """Internal use only"""

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
    """Saved race attributes are simple storage variables which persist to the database. Saved race attribute values are unique to/stored individually for each saved race."""
    __tablename__ = 'saved_race_meta_attribute'
    __table_args__ = (
        DB.UniqueConstraint('id', 'name'),
    )
    id:int = DB.Column(DB.Integer, DB.ForeignKey("saved_race_meta.id"), nullable=False, primary_key=True)
    """ID of saved race to which this attribute is assigned"""
    name = DB.Column(DB.String(80), nullable=False, primary_key=True)
    """Name of attribute"""
    value = DB.Column(DB.String(), nullable=True)
    """Value of attribute"""

class SavedPilotRace(Base):
    """Pilot Runs store data related to individual pilots in each race, except lap crossings. Each saved race has one or more pilot runs associated with it."""
    __tablename__ = 'saved_pilot_race'
    __table_args__ = (
        DB.UniqueConstraint('race_id', 'node_index'),
    )
    id:int = DB.Column(DB.Integer, primary_key=True)
    """Internal identifier"""
    race_id:int = DB.Column(DB.Integer, DB.ForeignKey("saved_race_meta.id"), nullable=False)
    """ID of associated saved race"""
    node_index:int = DB.Column(DB.Integer, nullable=False)
    """Seat number"""
    pilot_id:int = DB.Column(DB.Integer, DB.ForeignKey("pilot.id"), nullable=False)
    """ID of associated pilot"""
    history_values:str = DB.Column(DB.String, nullable=True)
    """JSON-serialized raw RSSI data"""
    history_times:str = DB.Column(DB.String, nullable=True)
    """JSON-serialized timestamps for raw RSSI data"""
    penalty_time:int = DB.Column(DB.Integer, nullable=False)
    """Not implemented"""
    penalty_desc:int = DB.Column(DB.String, nullable=True)
    """Not implemented"""
    enter_at:int = DB.Column(DB.Integer, nullable=False)
    """Gate enter calibration point"""
    exit_at:int = DB.Column(DB.Integer, nullable=False)
    """Gate exit calibration point"""
    frequency:int = DB.Column(DB.Integer, nullable=True)
    """Active frequency for this seat at race time"""

    def __repr__(self):
        return '<SavedPilotRace %r>' % self.id

class LapSource:
    """Describes the method used to enter a lap into the database"""
    
    REALTIME = 0
    """Lap added by (hardware) interface in real time"""
    MANUAL = 1
    """Lap added manually by user in UI"""
    RECALC = 2
    """Lap added after recalculation (marshaling) or RSSI data"""
    AUTOMATIC = 3
    """Lap added by other automatic process"""
    API = 4
    """Lap added by API (plugin)"""

class SavedRaceLap(Base):
    """Laps store data related to start gate crossings. Each pilot run may have one or more laps associated with it. When displaying laps, be sure to reference the associated race format."""
    
    __tablename__ = 'saved_race_lap'
    id:int = DB.Column(DB.Integer, primary_key=True)
    """Internal identifier"""
    race_id:int = DB.Column(DB.Integer, DB.ForeignKey("saved_race_meta.id"), nullable=False)
    """ID of associated saved race"""
    pilotrace_id:int = DB.Column(DB.Integer, DB.ForeignKey("saved_pilot_race.id"), nullable=False)
    """ID of associated pilot run"""
    node_index:int = DB.Column(DB.Integer, nullable=False)
    """Seat number"""
    pilot_id:int = DB.Column(DB.Integer, DB.ForeignKey("pilot.id"), nullable=False)
    """ID of associated pilot"""
    lap_time_stamp:int = DB.Column(DB.Float, nullable=False)
    """Milliseconds since race start time"""
    lap_time:int = DB.Column(DB.Float, nullable=False)
    """Milliseconds since previous counted lap"""
    lap_time_formatted:str = DB.Column(DB.String, nullable=False)
    """Formatted user-facing text"""
    source:LapSource = DB.Column(DB.Integer, nullable=False)
    """Lap source type"""
    deleted:bool = DB.Column(DB.Boolean, nullable=False)
    """True if record should not be counted in results calculations"""

    def __repr__(self):
        return '<SavedRaceLap %r>' % self.id

class Profiles(Base):
    """Frequency sets contain a mapping of band/channel/frequency values to seats. They also store enter and exit values.
    
    frequencies can be JSON-unserialized (json.loads) to a dict:

        b: list of band designations, ordered by seat number; values may string be null

        c: list of band-channel designations, ordered by seat number; values may int be null

        f: list of frequencies, ordered by seat number; values are int

    enter_ats and exit_ats can be JSON-unserialized (json.loads) to a dict:

            v: list of enter/exit values, ordered by seat number; values are int

    The length of lists stored in frequencies, enter_ats, and exit_ats may not match the number of seats. In these cases values are either not yet available (if too few) or no longer used (if too many) for higher-index seats.

    The sentinel value RHUtils.FREQUENCY_ID_NONE should be used when no frequency is defined.

    Notice: The frequency set specification is expected to be modified in future versions. Please consider this while developing plugins.

        Rename class

        Siimplify serialization for enter_ats, exit_ats

        Remove of unused f_ratio
    """
    __tablename__ = 'profiles'
    id:int = DB.Column(DB.Integer, primary_key=True)
    """Internal identifier"""
    name:str = DB.Column(DB.String(80), nullable=False)
    """User-facing name"""
    description:str = DB.Column(DB.String(256), nullable=True)
    """User-facing long description"""
    frequencies:str = DB.Column(DB.String(80), nullable=False)
    """JSON-serialized frequency objects per seat"""
    enter_ats:str = DB.Column(DB.String(80), nullable=True)
    """JSON-serialized enter-at points per seat"""
    exit_ats:str = DB.Column(DB.String(80), nullable=True)
    """JSON-serialized exit-at points per seat"""
    f_ratio:int = DB.Column(DB.Integer, nullable=True)
    """Unused legacy value"""

class RaceFormat(Base):
    """Race formats are profiles of properties used to define parameters of individual races. Every race has an assigned format. A race formats may be assigned to a race class, which forces RotorHazard to switch to that formatwhen running races within the class.
    
    The sentinel value RHUtils.FORMAT_ID_NONE should be used when no race format is defined.

    Notice: The race format specification is expected to be modified in future versions. Please consider this while developing plugins.

        The type for staging_delay_tones may change to boolean.

        The type for unlimited_time may change to boolean.

        The type for win_condition may change to a members of dedicated class or become string-based for extensibility.

        The type for start_behavior may change to a members of dedicated class.
    """
    __tablename__ = 'race_format'
    id:int = DB.Column(DB.Integer, primary_key=True)
    """Internal identifier"""
    name:str = DB.Column(DB.String(80), nullable=False)
    """User-facing name"""
    unlimited_time:int = DB.Column('race_mode', DB.Integer, nullable=False)
    """True(1) if race clock counts up, False(0) if race clock counts down"""
    race_time_sec:int = DB.Column(DB.Integer, nullable=False)
    """Race clock duration in seconds, unused if unlimited_time is True(1)"""
    lap_grace_sec:int = DB.Column(DB.Integer, nullable=False, default=-1)
    """Grace period duration in seconds, -1 for unlimited, unused if unlimited_time is True(1)"""
    staging_fixed_tones:int = DB.Column(DB.Integer, nullable=False)
    """Number of staging tones always played regardless of random delay"""
    start_delay_min_ms:int = DB.Column(DB.Integer, nullable=False)
    """Minimum period for random phase of staging delay in milliseconds"""
    start_delay_max_ms:int = DB.Column(DB.Integer, nullable=False)
    """Maximum duration of random phase of staging delay in milliseconds"""
    staging_delay_tones = DB.Column('staging_tones', DB.Integer, nullable=False)
    """Whether to play :class:`StagingTones` each second during random delay phase"""
    number_laps_win:int = DB.Column(DB.Integer, nullable=False)
    """Number of laps used to declare race winner, if > 0"""
    win_condition = DB.Column(DB.Integer, nullable=False)
    """:class:`WinCondition` used to determine race winner and race ranking"""
    team_racing_mode:bool = DB.Column(DB.Boolean, nullable=False)
    """Whether local simultaneous team racing mode will be used"""
    start_behavior = DB.Column(DB.Integer, nullable=False)
    """Handling :class:`StartBehavior` of first crossing"""
    points_method = DB.Column(DB.String, nullable=True)
    """JSON-serialized arguments for points algorithm"""

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
    """Race Format Attributes are simple storage variables which persist to the database. Race Format Attribute values are unique to/stored individually for each race format."""
    __tablename__ = 'race_format_attribute'
    __table_args__ = (
        DB.UniqueConstraint('id', 'name'),
    )
    id:int = DB.Column(DB.Integer, DB.ForeignKey("race_format.id"), nullable=False, primary_key=True)
    """ID of race format to which this attribute is assigned"""
    name:str = DB.Column(DB.String(80), nullable=False, primary_key=True)
    """Name of attribute"""
    value:str = DB.Column(DB.String(), nullable=True)
    """Value of attribute"""

class GlobalSettings(Base):
    """Options are settings that apply to a server globally."""
    
    __tablename__ = 'global_settings'
    id:int = DB.Column(DB.Integer, primary_key=True)
    """Internal identifier"""
    option_name:str = DB.Column(DB.String(40), nullable=False)
    """Name of option"""
    option_value:str = DB.Column(DB.String, nullable=True)
    """Value of option"""

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

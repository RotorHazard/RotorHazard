'''Read-only access to a RotorHazard database file other than the live one.'''

import json
import logging
import os
import sqlite3
import tempfile
from urllib.parse import quote

import sqlalchemy
import Database

logger = logging.getLogger(__name__)

IN_MEMORY_NAME = '(in memory)'

_HAS_DESERIALIZE = hasattr(sqlite3.Connection, 'deserialize')  # Python 3.11+, with SQLite built to support it
_SQLITE_HEADER = b'SQLite format 3\x00'
_WAL_VERSIONS = b'\x02\x02'
_ROLLBACK_VERSIONS = b'\x01\x01'

class DatabaseRecord:
    '''A read-only row, with the attribute names of the live data object.'''
    def __init__(self, table_name, fields):
        object.__setattr__(self, '_table_name', table_name)
        object.__setattr__(self, '_fields', dict(fields))

    def __getattr__(self, name):
        try:
            return self._fields[name]
        except KeyError:
            raise AttributeError("'{}' record has no attribute '{}'".format(self._table_name, name)) from None

    def __setattr__(self, name, value):
        raise AttributeError("'{}' record is read-only".format(self._table_name))

    def asdict(self):
        return dict(self._fields)

    def __repr__(self):
        return '<{} {}>'.format(self._table_name, self._fields.get('id'))

def _model_columns(model):
    '''(attribute name, column name, type) of a model's columns, leaving out pickled and internal ones.'''
    return [(attr.key, attr.columns[0].name, attr.columns[0].type)
            for attr in sqlalchemy.inspect(model).column_attrs
            if not isinstance(attr.columns[0].type, sqlalchemy.PickleType) and not attr.key.startswith('_')]

def _readonly_uri(path):
    return 'file:{}?mode=ro'.format(quote(os.path.abspath(path).replace('\\', '/')))

def _without_wal(data):
    '''A database's contents, as a copy set to rollback journal mode if they are in WAL mode, which an
       in-memory database cannot read.'''
    view = memoryview(data).cast('B')
    if view[:16] == _SQLITE_HEADER and view[18:20] == _WAL_VERSIONS:
        copy = bytearray(view)
        copy[18:20] = _ROLLBACK_VERSIONS
        return copy
    return view

def _load_via_tempfile(conn, data):
    '''Copies a database's contents into a connection through a temporary file, deleted before returning.'''
    tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    try:
        with tmp:
            tmp.write(data)
        source = sqlite3.connect(_readonly_uri(tmp.name), uri=True)
        try:
            source.backup(conn)
        finally:
            source.close()
    finally:
        os.remove(tmp.name)

def _connect_bytes(data):
    '''Read-only in-memory connection holding a copy of a database's contents.'''
    data = _without_wal(data)
    conn = sqlite3.connect(':memory:', check_same_thread=False)
    try:
        if _HAS_DESERIALIZE:
            conn.deserialize(data)
        else:
            _load_via_tempfile(conn, data)
        conn.execute('PRAGMA query_only = ON')
    except BaseException:
        conn.close()
        raise
    return conn

def decode_history(pilotrun):
    '''(values, times) lists of a pilot run's RSSI history, empty when it has none.'''
    values = json.loads(pilotrun.history_values) if pilotrun.history_values else []
    times = json.loads(pilotrun.history_times) if pilotrun.history_times else []
    return values, times

class DatabaseReader:
    '''Opens a database file, or a database's contents as bytes, read-only and returns its saved races and
       their context as DatabaseRecords. Contents are read into memory and never written to a file, except
       briefly to a temporary one where SQLite cannot open them from memory. Each table is read by the
       columns the file has, so older versions open too: a column the file lacks reads as None.'''

    def __init__(self, source, server_api, name=None):
        self._conn = None
        self._columns = {}
        if isinstance(source, (bytes, bytearray, memoryview)):
            self.path = None
            self.name = name or IN_MEMORY_NAME
            self._label = self.name
            if not memoryview(source).nbytes:
                raise ValueError("Database contents are empty: {}".format(self._label))
        else:
            self.path = os.fspath(source)
            self.name = os.path.basename(self.path)
            self._label = self.path
            if not os.path.isfile(self.path):
                raise FileNotFoundError("Database file not found: {}".format(self.path))
        try:
            if self.path is None:
                self._conn = _connect_bytes(source)
            else:
                self._conn = sqlite3.connect(_readonly_uri(self.path), uri=True, check_same_thread=False)
            self._tables = {row[0] for row in self._conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        except sqlite3.DatabaseError as ex:
            self.close()
            raise ValueError("Not a readable database file: {} ({})".format(self._label, ex)) from None
        if 'saved_race_meta' not in self._tables:
            self.close()
            raise ValueError("Not a RotorHazard database with saved races: {}".format(self._label))
        option = self.option('server_api')
        self.server_api = int(option) if option is not None and str(option).isdigit() else 0
        if self.server_api > server_api:
            self.close()
            raise ValueError("Database version ({}) is newer than the server's ({}): {}".format(
                self.server_api, server_api, self._label))

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _file_columns(self, table_name):
        if table_name not in self._columns:
            self._columns[table_name] = {row[1] for row in self._conn.execute(
                'PRAGMA table_info("{}")'.format(table_name))}
        return self._columns[table_name]

    def _query(self, model, where=None, params=(), order_by='id'):
        '''Records of a model's table, by the columns the file has.'''
        table_name = model.__tablename__
        if self._conn is None:
            raise ValueError("Database file is closed: {}".format(self._label))
        if table_name not in self._tables:
            return []
        file_columns = self._file_columns(table_name)
        columns = _model_columns(model)
        read = [column for column in columns if column[1] in file_columns]
        sql = 'SELECT {} FROM "{}"'.format(', '.join('"{}"'.format(column[1]) for column in read), table_name)
        if where:
            sql += ' WHERE ' + where
        if order_by and order_by in file_columns:
            sql += ' ORDER BY "{}"'.format(order_by)
        records = []
        for row in self._conn.execute(sql, params):
            fields = {column[0]: None for column in columns}
            for (key, _, column_type), value in zip(read, row):
                if isinstance(column_type, sqlalchemy.Boolean) and value is not None:
                    value = bool(value)
                fields[key] = value
            records.append(DatabaseRecord(table_name, fields))
        return records

    def _by_id(self, model, record_id):
        records = self._query(model, '"id" = ?', (record_id,))
        return records[0] if records else None

    @property
    def races(self):
        return self._query(Database.SavedRaceMeta)

    def race_by_id(self, race_id):
        return self._by_id(Database.SavedRaceMeta, race_id)

    def races_by_heat(self, heat_id):
        return self._query(Database.SavedRaceMeta, '"heat_id" = ?', (heat_id,))

    @property
    def pilotruns(self):
        return self._query(Database.SavedPilotRace)

    def pilotrun_by_id(self, run_id):
        return self._by_id(Database.SavedPilotRace, run_id)

    def pilotruns_by_race(self, race_id):
        return self._query(Database.SavedPilotRace, '"race_id" = ?', (race_id,), order_by='node_index')

    def laps_by_pilotrun(self, run_id):
        return self._query(Database.SavedRaceLap, '"pilotrace_id" = ?', (run_id,), order_by='lap_time_stamp')

    @property
    def pilots(self):
        return self._query(Database.Pilot)

    def pilot_by_id(self, pilot_id):
        return self._by_id(Database.Pilot, pilot_id)

    @property
    def heats(self):
        return self._query(Database.Heat)

    def heat_by_id(self, heat_id):
        return self._by_id(Database.Heat, heat_id)

    @property
    def raceclasses(self):
        return self._query(Database.RaceClass)

    def raceclass_by_id(self, raceclass_id):
        return self._by_id(Database.RaceClass, raceclass_id)

    @property
    def raceformats(self):
        return self._query(Database.RaceFormat)

    def raceformat_by_id(self, format_id):
        return self._by_id(Database.RaceFormat, format_id)

    def option(self, name, default=None):
        records = self._query(Database.GlobalSettings, '"option_name" = ?', (name,))
        return records[0].option_value if records else default

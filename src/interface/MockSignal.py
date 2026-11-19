'''Signal providers for the mock hardware interface.'''

import logging
import random
from dataclasses import dataclass

from BaseHardwareInterface import MarshalType

logger = logging.getLogger(__name__)

@dataclass
class SignalSample:
    '''One reading for a mock seat, as a node reports it.'''
    lap_id: int                 # count of passes completed; a change records a pass
    rssi: int                   # current RSSI
    cross_flag: bool            # whether a crossing is in progress
    ms_val: int = 0             # ms between the pass and this reading
    node_peak_rssi: int = 0
    pass_peak_rssi: int = 0
    pass_nadir_rssi: int = 0
    node_nadir_rssi: int = 0
    loop_time: int = 1
    # peak and nadir since the previous reading, recorded as RSSI history; times are ms before this reading
    peak_rssi: int = 0
    peak_first_time: int = 0
    peak_last_time: int = 0
    nadir_rssi: int = 0
    nadir_first_time: int = 0
    nadir_last_time: int = 0
    history_flag: bool = True   # False records no RSSI history, as pass-peak-only hardware
    read_time: float = None     # monotonic time of the reading, if not the time it is read

class MockSignalProvider:
    '''Base for a mock signal source. The mock interface calls read() for each seat with a frequency on
       every update, inside its update greenlet, so no method may block.'''
    marshal_type = MarshalType.FULL_RSSI
    label_detail = ''           # shown after the label on the Advanced Settings page

    def start(self):
        '''Called when this provider becomes the active signal.'''

    def stop(self):
        '''Called when another provider becomes the active signal.'''

    def on_race_status(self, status):
        '''Called with each race status change while active.'''

    def read(self, node, now):
        '''Returns a SignalSample for the node (a seat object, as in 'rhapi.interface.seats'), a list of them in
           time order, or None for no reading; 'now' is the monotonic read time.'''
        return None

@dataclass
class MockSignalEntry:
    name: str
    label: str
    provider: MockSignalProvider

_signals = {}

def register_signal(name, label, provider):
    '''Adds a provider under a name; returns False if the name is taken.'''
    name = str(name)
    if name in _signals:
        logger.warning("Mock signal '{}' already registered".format(name))
        return False
    _signals[name] = MockSignalEntry(name, label, provider)
    return True

def get_signal(name):
    return _signals.get(str(name))

def get_signals():
    return list(_signals.values())

class NoSignal(MockSignalProvider):
    pass

class ReplayCsvSignal(MockSignalProvider):
    '''Readings from 'mock_data_<n>.csv' in the data directory, in the format the hardware interface logs them, looping.
       Each reading is given at its recorded time when the file's read times rise steadily; otherwise one per update.'''
    label_detail = 'mock_data_[n].csv'
    MAX_READINGS_PER_UPDATE = 200

    def __init__(self):
        self._replays = {}

    def start(self):
        self._replays = {}

    def stop(self):
        self._replays = {}

    @staticmethod
    def _parse(line):
        '''(read time or None, sample fields) for a line, or None if it is malformed.'''
        cols = line.strip().split(',')
        if len(cols) < 16:
            return None
        try:
            fields = {
                'lap_id': int(cols[1]),
                'ms_val': int(cols[2]),
                'rssi': int(cols[3]),
                'node_peak_rssi': int(cols[4]),
                'pass_peak_rssi': int(cols[5]),
                'loop_time': int(cols[6]),
                'cross_flag': (cols[7] == 'T'),
                'pass_nadir_rssi': int(cols[8]),
                'node_nadir_rssi': int(cols[9]),
                'peak_rssi': int(cols[10]),
                'peak_first_time': int(cols[11]),
                'peak_last_time': int(cols[12]),
                'nadir_rssi': int(cols[13]),
                'nadir_first_time': int(cols[14]),
                'nadir_last_time': int(cols[15]),
            }
        except ValueError:
            return None
        try:
            read_time = float(cols[0])
        except ValueError:
            read_time = None
        return read_time, fields

    def _replay(self, index):
        if index not in self._replays:
            self._replays[index] = self._load("mock_data_{0}.csv".format(index+1))
        return self._replays[index]

    def _load(self, path):
        try:
            with open(path) as f:
                lines = f.readlines()
        except IOError:
            return None
        records = []
        bad_count = 0
        for line in lines:
            if line.strip():
                record = self._parse(line)
                if record:
                    records.append(record)
                else:
                    bad_count += 1
        if bad_count:
            logger.warning("Skipped {} malformed line(s) in {}".format(bad_count, path))
        if not records:
            return None
        times = [record[0] for record in records]
        timed = None not in times and all(later > earlier for earlier, later in zip(times, times[1:]))
        logger.info("Loaded {} ({} readings{})".format(path, len(records), ', at recorded times' if timed else ''))
        return {'records': records, 'timed': timed, 'pos': 0, 'base_now': None, 'base_time': None}

    def read(self, node, now):
        replay = self._replay(node.index)
        if not replay:
            return None
        records = replay['records']
        if not replay['timed']:
            fields = records[replay['pos']][1]
            replay['pos'] = (replay['pos'] + 1) % len(records)
            return SignalSample(**fields)
        samples = []
        while len(samples) < self.MAX_READINGS_PER_UPDATE:
            if replay['pos'] >= len(records):  # loop, starting over from now
                replay['pos'] = 0
                replay['base_now'] = None
            read_time, fields = records[replay['pos']]
            if replay['base_now'] is None:
                replay['base_now'] = now
                replay['base_time'] = read_time
            due = replay['base_now'] + read_time - replay['base_time']
            if due > now:
                break
            samples.append(SignalSample(read_time=due, **fields))
            replay['pos'] += 1
        return samples

class SimulatedSignal(MockSignalProvider):
    '''Random crossings: a pass starts on about 5% of readings and ends on about half.'''

    def __init__(self, marshal_type=MarshalType.FULL_RSSI, history_flag=True):
        self.marshal_type = marshal_type
        self.history_flag = history_flag
        self._state = {}

    def read(self, node, now):
        state = self._state.setdefault(node.index, {
            'lap_number': 0,
            'is_crossing': False,
            'pass_peak_rssi': 0,
            'pass_nadir_rssi': 100,
        })
        if state['is_crossing']:
            new_rssi = random.randrange(60,150)
            sample = SignalSample(
                lap_id=state['lap_number'],
                rssi=new_rssi,
                cross_flag=True,
                node_peak_rssi=100,
                pass_peak_rssi=max(state['pass_peak_rssi'], new_rssi),
                pass_nadir_rssi=state['pass_nadir_rssi'],
                node_nadir_rssi=20,
                peak_rssi=new_rssi,
                nadir_rssi=new_rssi,
                history_flag=self.history_flag,
            )
            if random.random() < 0.5:
                state['is_crossing'] = False
                state['pass_nadir_rssi'] = 100
        else:
            new_rssi = random.randrange(20,40)
            sample = SignalSample(
                lap_id=state['lap_number'],
                rssi=new_rssi,
                cross_flag=False,
                node_peak_rssi=100,
                pass_peak_rssi=state['pass_peak_rssi'],
                pass_nadir_rssi=min(state['pass_nadir_rssi'], new_rssi),
                node_nadir_rssi=20,
                peak_rssi=new_rssi,
                nadir_rssi=new_rssi,
                history_flag=self.history_flag,
            )
            if random.random() < 0.05:
                state['lap_number'] += 1
                state['is_crossing'] = True
                state['pass_peak_rssi'] = 0
        return sample

# built-in signals, numbered as the 'MOCK_NODE_SIGNAL' setting values they had before providers
register_signal('0', 'None', NoSignal())
register_signal('1', 'Replay', ReplayCsvSignal())
register_signal('2', 'Simulated', SimulatedSignal())
register_signal('3', 'Simulated - Pass Peak Only', SimulatedSignal(MarshalType.PASS_PEAK_ONLY, history_flag=False))
register_signal('4', 'Simulated - Pass Peak Only (+RSSI)', SimulatedSignal(MarshalType.PASS_PEAK_ONLY))

import gevent
import bisect

def unpack_8(data):
    return data[0]


def pack_8(data):
    return [int(data & 0xFF)]


def unpack_16(data):
    '''Returns the full variable from 2 bytes input.'''
    result = data[0]
    result = (result << 8) | data[1]
    return result


def pack_16(data):
    '''Returns a 2 part array from the full variable.'''
    part_a = (data >> 8) & 0xFF
    part_b = (data & 0xFF)
    return [int(part_a), int(part_b)]


def unpack_32(data):
    '''Returns the full variable from 4 bytes input.'''
    result = data[0]
    result = (result << 8) | data[1]
    result = (result << 8) | data[2]
    result = (result << 8) | data[3]
    return result


def pack_32(data):
    '''Returns a 4 part array from the full variable.'''
    part_a = (data >> 24) & 0xFF
    part_b = (data >> 16) & 0xFF
    part_c = (data >> 8) & 0xFF
    part_d = (data & 0xFF)
    return [int(part_a), int(part_b), int(part_c), int(part_d)]


def calculate_checksum(data: bytearray):
    checksum = sum(data) & 0xFF
    return checksum


def ensure_iter(l):
    if not hasattr(l, '__iter__'):
        l = [l]
    return l


class RssiHistory:
    def __init__(self):
        # monotonic timestamps (secs)
        self._times = []
        self._values = []
        self.lock = gevent.lock.RLock()

    def __len__(self):
        assert len(self._times) == len(self._values)
        return len(self._times)

    def append(self, ts, rssi):
        with self.lock:
            n = len(self._times)
            # if previous two entries have same value then just extend time on last entry
            if n >= 2 and self._values[n-1] == rssi and self._values[n-2] == rssi:
                self._times[n-1] = ts
            else:
                self._times.append(ts)
                self._values.append(rssi)

    def merge(self, new_entries):
        with self.lock:
            for ts_rssi in new_entries:
                idx = bisect.bisect_left(self._times, ts_rssi[0])
                if idx < len(self._times) and ts_rssi[0] == self._times[idx]:
                    # replace existing value
                    self._values[idx] = ts_rssi[1]
                else:
                    self._times.insert(idx, ts_rssi[0])
                    self._values.insert(idx, ts_rssi[1])
            
    def set(self, times, values):
        if len(times) != len(values):
            raise ValueError("History time and value lists must have the same length")
        with self.lock:
            self._times = times
            self._values = values

    def get(self):
        with self.lock:
            return self._times.copy(), self._values.copy()

    def prune(self, keep_after):
        with self.lock:
            prune_idx = bisect.bisect_left(self._times, keep_after)
            del self._values[:prune_idx]
            del self._times[:prune_idx]


class ExtremumFilter:
    def __init__(self):
        self.previous = 0
        self.delta = 0

    def filter(self, x):
        '''Includes inflexion points'''
        new_delta = x - self.previous
        if self.delta > 0 and new_delta <= 0:
            y = self.previous
        elif self.delta < 0 and new_delta >= 0:
            y = self.previous
        elif self.delta == 0 and new_delta != 0:
            y = self.previous
        else:
            y = None
        self.previous = x
        self.delta = new_delta
        return y


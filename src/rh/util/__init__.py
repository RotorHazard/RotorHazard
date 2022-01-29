from collections import deque
import math
from time import perf_counter_ns


def ms_counter() -> int:
    return round(perf_counter_ns()/1000000)


class Averager:
    """Tracks a running average, and min/max/last values"""
    def __init__(self, maxNumItems):
        self._n = maxNumItems
        self._reset()

    def _reset(self):
        self._data = deque()
        self._minVal = None
        self._maxVal = None
        self._lastVal = None
        self._avgVal = None
        self._totalVal = 0
        self._newAvgFlag = False

    def append(self, value):
        self._lastVal = value
        if len(self._data) >= self._n:
            if value < self._minVal:
                self._minVal = value
            elif value > self._maxVal:
                self._maxVal = value
            poppedVal = self._data.popleft()
            self._totalVal -= poppedVal
            self._data.append(value)
            self._totalVal += value
            self._newAvgFlag = True
            # if popped value was min/max then get new min/max from list
            if poppedVal <= self._minVal:
                self._minVal = min(self._data)
            if poppedVal >= self._maxVal:
                self._maxVal = max(self._data)
        else:
            self._data.append(value)
            self._totalVal += value
            if len(self._data) > 1:
                if value < self._minVal:
                    self._minVal = value
                elif value > self._maxVal:
                    self._maxVal = value
                self._newAvgFlag = True
            else:
                self._minVal = self._maxVal = self._avgVal = value

    def clear(self):
        self._reset()

    @property
    def min(self):
        return self._minVal

    @property
    def max(self):
        return self._maxVal

    @property
    def last(self):
        return self._lastVal

    @property
    def mean(self):
        if self._newAvgFlag:
            self._newAvgFlag = False
            self._avgVal = self._totalVal / len(self._data)
        return self._avgVal

    @property
    def std(self):
        sum_diff = 0
        mean = self.mean
        for val in self._data:
            diff = val - mean
            sum_diff += diff**2
        return math.sqrt(sum_diff/len(self._data)) if len(self._data) > 0 else None

    def formatted(self, decimalplaces=None, units=''):
        if decimalplaces is not None:
            formatter = lambda x: round(x, decimalplaces) if x is not None else x
        else:
            formatter = lambda x: x
        return "mean {}{}, std {}{}, min {}{}, max {}{}".format(
            formatter(self.mean), units,
            formatter(self.std), units,
            formatter(self.min), units,
            formatter(self.max), units
        )

    def __getitem__(self, item):
        return self._data[item]

    def __len__(self):
        return len(self._data)

    def __str__(self):
        return self.formatted()


import flask
import numpy as np


class StrictJsonEncoder(flask.json.JSONEncoder):
    def __init__(self, *args, **kwargs):
        kwargs['allow_nan'] = False
        super().__init__(*args, **kwargs)

    def default(self, o):
        if isinstance(o, np.generic):
            return o.item()
        else:
            return super().default(o)

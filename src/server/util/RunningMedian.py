# RunningMedian.py
# Efficient running median in plain Python
# https://github.com/thomedes/RunningMedian.py

def median(s):
    """Returns the median of the _already_sorted_ list s"""
    l = len(s)
    m = l // 2
    return s[m] if l % 2 else (s[m] + s[m - 1]) / 2

class NaiveRunningMedian:
    """Minimal implementation of Running Median

    works perfectly fine but is slow for big windows"""

    def __init__(self, window_size):
        self.window_   = []
        self.capacity_ = window_size

    def insert(self, x):
        self.window_.append(x)
        if len(self.window_) > self.capacity_:
            self.window_ = self.window_[1:]
        return self

    def median(self):
        return median(sorted(self.window_))

class SortedVector:
    """Keeps a sorteed list of all inserted elements"""
    def __init__(self):
        self.data_ = []

    def find_pos_(self, x):
        """Finds where given value is or should be"""

        (a, b) = (0, len(self.data_))

        while a < b:
            m = (a + b) // 2

            if self.data_[m] < x:
                a = m + 1
            else:
                b = m

        return a

    def insert(self, x):
        i = self.find_pos_(x)
        self.data_[i:i] = [x]

    def remove(self, x):
        i = self.find_pos_(x)
        del self.data_[i]

    def __getitem__(self, item): return self.data_[item]
    def __len__(self): return len(self.data_)

class RunningMedian:

    def __init__(self, window_size):
        self.ring_ = [None] * window_size
        self.head_ = 0
        self.sorted_ = SortedVector()

    def insert(self, x):
        current = self.ring_[self.head_]
        self.ring_[self.head_] = x
        self.head_ = (self.head_ + 1) % len(self.ring_)

        if current != None: self.sorted_.remove(current)
        self.sorted_.insert(x)

    def median(self):
        return median(self.sorted_)

def main():
    import random

    SAMPLES      = 100000
    WINDOW_SIZE  = 10000

    w = RunningMedian(WINDOW_SIZE)
    n = NaiveRunningMedian(WINDOW_SIZE) # For comparison checks

    for i in range(SAMPLES):
        sample = random.randint(0, 1000)

        w.insert(sample)
        wm = w.median()

        # Print something every 1000 samples
        if i % 1000 == 0: print("%5d\t%d" % (i, wm))

        # Check against naive implementation, change False to True
        if False:
            n.insert(sample)
            nm = n.median()

            assert nm == wm, "%d != %d" % (wm, nm)

if __name__ == "__main__":
    main()

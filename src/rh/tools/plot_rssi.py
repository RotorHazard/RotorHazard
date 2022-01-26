import numpy as np
from scipy.fft import rfft, rfftfreq
import matplotlib.pyplot as plt
import sys
import csv
import rh.util.persistent_homology as ph

rssis = []
with open(sys.argv[1]) as f:
    reader = csv.reader(f)
    for r in reader:
        rssis.append(float(r[0]))

fs = 1000 # sample freq
ts = np.arange(len(rssis))/fs
rssis = np.array(rssis)

from scipy.ndimage import median_filter
window_size = 5 # should be odd
rssis = median_filter(rssis, window_size, origin=(window_size-1)//2)

F = rfft(rssis, norm='forward')
freqs = rfftfreq(rssis.size, 1/fs)

fig, axs = plt.subplots(1, 2, figsize=(12,6))
axs[0].set_title('Signal')
axs[0].set_ylabel('RSSI')
axs[0].set_xlabel('Time / s')
axs[0].plot(ts, rssis)
axs[1].set_title('Spectrum')
axs[1].set_xlabel('Frequency / Hz')
axs[1].plot(freqs, np.abs(F))
fig.tight_layout()
plt.show()

ccs = ph.calculatePeakPersistentHomology(rssis)
ccs = ph.sortByLifetime(ccs)
fig, axs = plt.subplots(1, 2, figsize=(8,4))
axs[0].set_title('Persistence diagram')
ph.plotPersistenceDiagram(axs[0], ccs)
axs[1].set_title('Persistence lifetimes')
ph.plotLifetimes(axs[1], ccs)
fig.tight_layout()
plt.show()

import numpy as np
from scipy.fft import rfft, rfftfreq
import matplotlib.pyplot as plt
import sys
import csv
import rh.util.persistent_homology as ph
from scipy.ndimage import median_filter


fs = 1000  # sample freq
median_window_size = 5  # should be odd
ph_history_size = 12


rssi_list = []
with open(sys.argv[1]) as f:
    reader = csv.reader(f)
    for r in reader:
        rssi_list.append(float(r[0]))

ts = np.arange(len(rssi_list))/fs
rssis = np.array(rssi_list)

rssis = median_filter(rssis, median_window_size, origin=(median_window_size-1)//2)


def plot_signal(rssis):
    F = rfft(rssis, norm='forward')
    freqs = rfftfreq(len(rssis), 1/fs)

    fig, axs = plt.subplots(1, 2, figsize=(12,6))
    fig.canvas.manager.set_window_title('Signal')
    axs[0].set_title('Signal')
    axs[0].set_ylabel('RSSI')
    axs[0].set_xlabel('Time / s')
    axs[0].plot(ts, rssis)
    axs[1].set_title('Spectrum')
    axs[1].set_xlabel('Frequency / Hz')
    axs[1].plot(freqs, np.abs(F))
    fig.tight_layout()
    plt.show(block=False)


plot_signal(rssis)


def plot_ph(title, ccs):
    def add_threshold_line(axs, threshold):
        xlim = axs.get_xlim()
        axs.plot(xlim, [threshold, threshold], '--', c='tomato')
        axs.annotate('threshold', (xlim[0], threshold), xytext=(3,3), textcoords='offset points',  fontsize='x-small')

    def add_threshold_diagonal(axs, threshold):
        xlim = axs.get_xlim()
        axs.plot(xlim, [xlim[0] + threshold, xlim[1] + threshold], '--', c='tomato')

    def add_tooltip(axs):
        tooltip = axs.annotate('', (0,0), xytext=(3,3), textcoords='offset points', fontsize='x-small')
        tooltip.set_visible(False)
        axs._tooltip = tooltip

    def on_hover_tooltip(event):
        axs = event.inaxes
        if axs is not None and axs.collections and hasattr(axs, '_tooltip'):
            tooltip = axs._tooltip
            contains_values, info = axs.collections[0].contains(event)
            if contains_values:
                tooltip.xy = (event.xdata, event.ydata)
                tooltip.set_text("{} values".format(len(info['ind'])) if len(info['ind']) > 1 else "1 value")
                tooltip.set_visible(True)
            else:
                tooltip.xy = (0, 0)
                tooltip.set_text('')
                tooltip.set_visible(False)
            axs.get_figure().canvas.draw_idle()

    min_bound, max_bound = ph.findBreak(ccs)
    threshold = (min_bound + max_bound)/2

    fig, axs = plt.subplots(1, 3, figsize=(12,4))
    fig.canvas.manager.set_window_title(title)
    fig.canvas.mpl_connect('motion_notify_event', on_hover_tooltip)

    axs[0].set_title('Sample lifetimes')
    ph.plotSampleLifetimes(axs[0], ts, ccs)
    add_threshold_line(axs[0], threshold)

    axs[1].set_title('Persistence diagram')
    ph.plotPersistenceDiagram(axs[1], ccs)
    add_threshold_diagonal(axs[1], threshold)
    add_tooltip(axs[1])

    axs[2].set_title('Persistence lifetimes')
    ph.plotLifetimes(axs[2], ccs)
    add_threshold_line(axs[2], threshold)
    add_tooltip(axs[2])

    fig.tight_layout()
    plt.show(block=False)


ccs = ph.calculatePeakPersistentHomology(rssis)
ccs = ph.sortByLifetime(ccs)
plot_ph('Persistent Homology', ccs)

rt_ccs = [ph.calculateRealtimePeakPersistentHomology(rssis[:i+1], ph_history_size) for i in range(len(rssis))]
rt_ccs = ph.sortByLifetime([cc for cc in rt_ccs if cc is not None])
plot_ph('Realtime Persistent Homology', rt_ccs)

plt.show()

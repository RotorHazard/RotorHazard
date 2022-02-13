import numpy as np
import jenkspy
import scipy.signal as signal


class ConnectedComponent:
	def __init__(self, idx, birth, death):
		self.left = idx
		self.right = idx
		self.birth = birth
		self.death = death

	def __str__(self):
		return "{} -> {} ({})".format(self.birth[1], self.death[1], self.lifetime())

	def __repr__(self):
		return "{} -> {}".format(self.birth, self.death)

	def to_pair(self):
		return [self.birth[1], self.death[1]]

	def to_upair(self):
		'''Unsigned/unordered pair'''
		return [self.death[1], self.birth[1]] if self.death[1] < self.birth[1] else [self.birth[1], self.death[1]]

	def lifetime(self):
		return abs(self.birth[1] - self.death[1])


def calculatePeakPersistentHomology(data):
	ccs = []
	N = len(data)
	idxToCC = [None]*N
	sorted_idxs = sorted(range(N), key=lambda i: (data[i], -i), reverse=True)
	min_idx = sorted_idxs[-1]

	def arrange_peak_centers():
		k = 0
		while k < N:
			# prefer peak centers
			end = k
			while end < N-1 and sorted_idxs[end+1] == sorted_idxs[end] + 1 and data[sorted_idxs[end+1]] == data[sorted_idxs[end]]:
				end += 1
			end += 1  # exclusive
			if end - k > 2:
				mid = (k + end - 1)//2
				# rearrange to do the peak center first
				left_part = sorted_idxs[k:mid]
				left_part.reverse()
				right_part = sorted_idxs[mid:end]
				sorted_idxs[k:end] = right_part + left_part
			k = end

	arrange_peak_centers()

	for i in sorted_idxs:
		leftCC = idxToCC[i-1] if i > 0 else None
		rightCC = idxToCC[i+1] if i < N-1 else None
		if leftCC is None and rightCC is None:
			cc = ConnectedComponent(i, (i, data[i]), (min_idx, data[min_idx]))
			ccs.append(cc)
			idxToCC[i] = cc
		elif leftCC is not None and rightCC is None:
			leftCC.right += 1
			idxToCC[i] = leftCC
		elif leftCC is None and rightCC is not None:
			rightCC.left -= 1
			idxToCC[i] = rightCC
		else:
			if leftCC.birth[1] > rightCC.birth[1]:
				rightCC.death = (i, data[i])
				leftCC.right = rightCC.right
				idxToCC[i] = leftCC
				idxToCC[leftCC.right] = leftCC
			else:
				leftCC.death = (i, data[i])
				rightCC.left = leftCC.left
				idxToCC[i] = rightCC
				idxToCC[rightCC.left] = rightCC

	return ccs


def sortByLifetime(ccs):
	'''Sorts in descending order (i.e. most prominent first)'''
	return sorted(ccs, key=lambda cc: cc.lifetime(), reverse=True)


def calculateRealtimePeakPersistentHomology(rssi_history, window_size):
	'''rssi_history is a list containing all past RSSIs up-to and including the current time'''
	if not type(rssi_history) is np.ndarray:
		rssi_history = np.array(rssi_history)
	n = len(rssi_history)
	current_rssi = rssi_history[-1]
	peak_idxs = signal.find_peaks(rssi_history)[0]
	nadir_idxs = signal.find_peaks(-rssi_history)[0]
	idxs = np.sort(np.hstack([peak_idxs, nadir_idxs]))
	window_idxs = idxs[-window_size:]
	rssi_window = np.hstack([rssi_history[window_idxs], [current_rssi]])
	ccs = calculatePeakPersistentHomology(rssi_window)
	last_pos = len(rssi_window) - 1
	for cc in ccs:
		if cc.birth[0] == last_pos:
			if cc.death < cc.birth:
				cc.death = (window_idxs[cc.death[0]], cc.death[1])
			else:
				cc.death = (n - 1, cc.death[1])
			cc.birth = (n - 1, cc.birth[1])
			return cc
	return None


def findBreak(ccs):
	lifetimes = [cc.lifetime() for cc in ccs]
	breaks = jenkspy.jenks_breaks(lifetimes, nb_class=2)
	levels = np.unique(lifetimes)
	i = np.min(np.nonzero(levels==breaks[1])[0])
	return (levels[i], levels[i+1])


def plotSampleLifetimes(axs, ts, ccs):
	ccs = sorted(ccs, key=lambda cc: cc.birth[0])
	data = np.array([[ts[cc.birth[0]], cc.lifetime()] for cc in ccs])
	axs.set_xlim((ts[0], ts[-1]))
	axs.set_xlabel('Time / s')
	axs.set_ylabel('Lifetime')
	axs.plot(data[:,0], data[:,1])


def plotPersistenceDiagram(axs, ccs):
	data = np.array([cc.to_pair() for cc in ccs])
	axs.scatter(data[:,1], data[:,0], s=2, color='blue')
	minv = np.min(data)*0.95
	maxv = np.max(data)*1.05
	axs.set_xlim((minv, maxv))
	axs.set_ylim((minv, maxv))
	axs.set_xlabel('Death')
	axs.set_ylabel('Birth')
	axs.plot([minv,maxv], [minv,maxv], "--", c='gray')


def plotLifetimes(axs, ccs):
	data = np.array([[cc.death[1], cc.lifetime()] for cc in ccs])
	axs.scatter(data[:,0], data[:,1], s=2, color='blue')
	minx = np.min(data[:,0])*0.95
	maxx = np.max(data[:,0])*1.05
	miny = np.min(data[:,1])*0.95
	maxy = np.max(data[:,1])*1.05
	axs.set_xlim((minx, maxx))
	axs.set_ylim((miny, maxy))
	axs.set_xlabel('Death')
	axs.set_ylabel('Lifetime')

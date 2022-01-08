import numpy as np
import jenkspy

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
	sorted_idxs = sorted(range(N), key=lambda i: data[i], reverse=True)
	min_idx = sorted_idxs[-1]

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


def findBreak(ccs):
	lifetimes = [cc.lifetime() for cc in ccs]
	breaks = jenkspy.jenks_breaks(lifetimes, nb_class=2)
	levels = np.unique(lifetimes)
	i = np.min(np.nonzero(levels==breaks[1])[0])
	return (levels[i], levels[i+1])


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

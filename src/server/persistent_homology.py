
class ConnectedComponent:
	def __init__(self, idx, birth, death):
		self.left = idx
		self.right = idx
		self.birth = birth
		self.death = death

	def __repr__(self):
		return "{} -> {}".format(self.birth, self.death)

	def to_pair(self):
		return [self.birth[1], self.death[1]]

	def lifetime(self):
		return self.birth[1] - self.death[1]
	
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

def testPeakPersistentHomology():
	data = [30, 29, 41, 4, 114, 1, 3, 2, 33, 9, 112, 40, 118]
	ph = calculatePeakPersistentHomology(data)
	ph = sorted(ph, key=lambda cc: cc.lifetime(), reverse=True)
	assert str(ph) == '[(12, 118) -> (5, 1), (4, 114) -> (5, 1), (10, 112) -> (11, 40), (2, 41) -> (3, 4), (8, 33) -> (9, 9), (0, 30) -> (1, 29), (6, 3) -> (7, 2)]'

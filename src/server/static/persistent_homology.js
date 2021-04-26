
function ConnectedComponent(idx, birth, death) {
	this.left = idx;
	this.right = idx;
	this.birth = birth;
	this.death = death;
	this.toString = function() {
		return "("+this.birth+") -> ("+this.death+")";
	};
	this.lifetime = function() {
		return this.birth[1] - this.death[1];
	};
}
	
function calculatePeakPersistentHomology(data) {
	const ccs = [];
	const N = data.length;
	const idxToCC = new Array(N);
	let sorted_idxs = new Array(N);
	for (let i=0; i<N; i++) {
		idxToCC[i] = null;
		sorted_idxs[i] = i;
	}
	sorted_idxs = sorted_idxs.sort(function(i, j) {
		return data[j] - data[i];
	});
	const min_idx = sorted_idxs[N-1];

	for (let i of sorted_idxs) {
		const leftCC = (i > 0) ? idxToCC[i-1] : null;
		const rightCC = (i < N-1) ? idxToCC[i+1] : null;
		if (leftCC === null && rightCC === null) {
			cc = new ConnectedComponent(i, [i, data[i]], [min_idx, data[min_idx]])
			ccs.push(cc)
			idxToCC[i] = cc
		} else if (leftCC !== null && rightCC === null) {
			leftCC.right += 1
			idxToCC[i] = leftCC
		} else if (leftCC === null && rightCC !== null) {
			rightCC.left -= 1
			idxToCC[i] = rightCC
		} else {
			if (leftCC.birth[1] > rightCC.birth[1]) {
				rightCC.death = [i, data[i]]
				leftCC.right = rightCC.right
				idxToCC[i] = leftCC
				idxToCC[leftCC.right] = leftCC
			} else {
				leftCC.death = [i, data[i]]
				rightCC.left = leftCC.left
				idxToCC[i] = rightCC
				idxToCC[rightCC.left] = rightCC
			}
		}
	}
	return ccs
}

function testPeakPersistentHomology() {
	const data = [30, 29, 41, 4, 114, 1, 3, 2, 33, 9, 112, 40, 118];
	let ph = calculatePeakPersistentHomology(data);
	ph = ph.sort(function(i, j) {
		return j.lifetime() - i.lifetime();
	});
	if (ph != '(12,118) -> (5,1),(4,114) -> (5,1),(10,112) -> (11,40),(2,41) -> (3,4),(8,33) -> (9,9),(0,30) -> (1,29),(6,3) -> (7,2)') {
		throw "AssertionError";
	}
}

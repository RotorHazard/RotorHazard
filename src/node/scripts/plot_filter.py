import csv
import sys
import numpy as np
import matplotlib.pyplot as plt

rows = []
with open(sys.argv[1]) as f:
	reader = csv.reader(f)
	header = next(reader)
	for r in reader:
		rows.append(np.array([float(r[0]), float(r[1]), float(r[2])]))

data = np.array(rows)
plt.plot(data[1000:2000,1:3])
plt.show()

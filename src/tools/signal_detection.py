import sys
import csv
from server import Database
from flask import Flask
import json
from interface import persistent_homology as ph
import matplotlib.pyplot as plt

def load_races(db_file):
	APP = Flask(__name__)
	APP.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../' + db_file
	APP.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
	DB = Database.DB
	DB.init_app(APP)
	DB.app = APP
	
	races = []
	
	q = DB.session.query( \
			Database.SavedPilotRace.id, \
			Database.SavedRaceMeta.round_id, \
			Database.SavedRaceMeta.heat_id, \
			Database.SavedPilotRace.node_index, \
			Database.SavedPilotRace.pilot_id, \
			DB.func.count(Database.SavedRaceLap.id), \
			Database.SavedPilotRace.history_times,
			Database.SavedPilotRace.history_values) \
		.join(Database.SavedRaceMeta, Database.SavedPilotRace.race_id==Database.SavedRaceMeta.id) \
		.outerjoin(Database.SavedRaceLap, (Database.SavedPilotRace.id==Database.SavedRaceLap.pilotrace_id) & (Database.SavedRaceMeta.id==Database.SavedRaceLap.race_id)) \
		.group_by(Database.SavedRaceMeta.round_id,Database.SavedRaceMeta.heat_id,Database.SavedPilotRace.pilot_id,Database.SavedPilotRace.history_values)
	for rec in q:
		history_times = json.loads(rec[-2])
		history_values = json.loads(rec[-1])
		races.append(rec[0:-2] + (history_times,history_values))
	races.sort(key=lambda race: race[0])
	return races


def list_races(races):
	for i, race in enumerate(races):
		print("[{}] ID {} round {} heat {} node {} pilot {} laps {}".format(i, *race[0:-2]))


def analyze_race(race, show_plots=True):
	print("ID {} round {} heat {} node {} pilot {} laps {}".format(*race[0:-2]))
	rssi_values = race[-1]
	if rssi_values:
		ccs = ph.calculatePeakPersistentHomology(rssi_values)
		ccs = ph.sortByLifetime(ccs)
		lap_count = race[-3]
		n = lap_count if lap_count else len(ccs)
		print("Top {} peaks:\n{}".format(n, [str(cc) for cc in ccs[0:n]]))
		min_bound, max_bound = ph.findBreak(ccs)
		threshold = (min_bound + max_bound)/2
		print("Estimated laps ({}): {}\n".format(threshold, len([cc for cc in ccs if cc.lifetime()>threshold])))
		if show_plots:
			_fig, axs = plt.subplots(1, 3, figsize=(8,4))
			axs[0].plot(race[-2], race[-1])
			ph.plotPersistenceDiagram(axs[1], ccs)
			ph.plotLifetimes(axs[2], ccs)
			plt.show()
		return (race[3], min_bound, max_bound)
	else:
		return (race[3], 0, 255)


def export(race, csv_path):
	with open(csv_path, 'w', newline='') as f:
		writer = csv.writer(f)
		for i in range(len(race[-2])):
			writer.writerow([int(race[-2][i]*1000), race[-1][i]])


if __name__ == '__main__':
	db_file = sys.argv[1] if len(sys.argv) > 1 else 'database.db'
	races = load_races(db_file)
	node_bounds = {}
	for race in races:
		node, min_bound, max_bound = analyze_race(race, show_plots=False)
		if node not in node_bounds:
			node_bounds[node] = ([], [])
		node_bounds[node][0].append(min_bound)
		node_bounds[node][1].append(max_bound)
	for node, bounds in node_bounds.items():
		lower_bound = max(bounds[0])
		upper_bound = min(bounds[1])
		threshold = (lower_bound + upper_bound)/2
		print("Node {}: threshold {}".format(node, threshold))

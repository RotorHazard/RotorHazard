import sys
from pathlib import Path
import csv
import Database
from flask import Flask
import json
from persistent_homology import calculatePeakPersistentHomology
import numpy as np
import matplotlib.pyplot as plt

db_file = sys.argv[1] if len(sys.argv) > 1 else 'database.db'

APP = Flask(__name__)
APP.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + db_file
APP.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
DB = Database.DB
DB.init_app(APP)
DB.app = APP

races = []

q = DB.session.query( \
		Database.SavedPilotRace.id, \
		Database.SavedRaceMeta.round_id, \
		Database.SavedRaceMeta.heat_id, \
		Database.SavedPilotRace.pilot_id, \
		DB.func.count(Database.SavedRaceLap.id), \
		Database.SavedPilotRace.history_times,
		Database.SavedPilotRace.history_values) \
	.filter(Database.SavedRaceMeta.id==Database.SavedPilotRace.race_id) \
	.filter(Database.SavedRaceMeta.id==Database.SavedRaceLap.race_id) \
	.filter(Database.SavedPilotRace.id==Database.SavedRaceLap.pilotrace_id) \
	.group_by(Database.SavedRaceMeta.round_id,Database.SavedRaceMeta.heat_id,Database.SavedPilotRace.pilot_id,Database.SavedPilotRace.history_values)
for rec in q:
	history_times = json.loads(rec[-2])
	history_values = json.loads(rec[-1])
	races.append(rec[0:-2] + (history_times,history_values))

def plot_race(race):
	print("ID {} round {} heat {} pilot {} laps {}".format(*race[0:-2]))
	ph = calculatePeakPersistentHomology(race[-1])
	ph = sorted(ph, key=lambda cc: cc.lifetime(), reverse=True)
	data = np.array([cc.to_pair() for cc in ph])
	print("Top peaks:\n{}".format(data[0:race[-3]]))
	fig, axs = plt.subplots(1, 2, figsize=(8,4))
	axs[0].plot(race[-2], race[-1])
	axs[1].scatter(data[:,1], data[:,0], s=2, color='blue')
	minv = np.min(data)-5
	maxv = np.max(data)+5
	axs[1].set_xlim((minv, maxv))
	axs[1].set_ylim((minv, maxv))
	axs[1].plot([minv,maxv],[minv,maxv], "--", c='gray')
	plt.show()
	
def export(race):
	db_path = Path(db_file)
	csv_path = '{}_race{}.csv'.format(db_path.stem, race[0])
	with open(csv_path, 'w', newline='') as f:
		writer = csv.writer(f)
		for i in range(len(race[-2])):
			writer.writerow([int(race[-2][i]*1000), race[-1][i]])

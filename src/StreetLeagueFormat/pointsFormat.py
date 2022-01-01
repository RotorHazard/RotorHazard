import json

def getLatestResultsFile():
	return open("results.json")

def getRaceResults(resultsFile):
	raceResults = json.load(resultsFile)
	return raceResults

def calculateRoundPoints(raceResults):
	SLRounds = []

	raceClasses = raceResults['classes'];

	for roundNumber in raceClasses:
		SLRounds.append([])
		pilotHeats = raceClasses[roundNumber]['leaderboard']['by_race_time']
		points = len(pilotHeats)
		for pilotHeat in pilotHeats:
			callsign = pilotHeat['callsign']
			heatTime = pilotHeat['total_time_raw']
			laps = pilotHeat['laps']
			pilotID = pilotHeat['pilot_id']
			SLRounds[-1].append({"callsign":callsign,"points":points,"laps":laps,"heatTime":heatTime})
			points -= 1
	return SLRounds

def getPilotTotalsFromRounds(rounds):
	pilotPoints = {}

	#add up the points for each pilot
	for i in range(0,len(rounds)):
		round = rounds[i]
		print("--- round "+str(i+1))
		for pilotHeat in round:
			callsign = pilotHeat['callsign']
			pilotRoundPoints = pilotHeat['points']
			if callsign in pilotPoints:
				pilotPoints[callsign]=pilotPoints[callsign]+pilotRoundPoints
			else:
				pilotPoints[callsign] = pilotRoundPoints
			print(callsign+", "+str(pilotRoundPoints))
	#sort the pilots by most points
	pilotPoints = dict(sorted(pilotPoints.items(), key = lambda kv: kv[1], reverse=True))
	for callsign in pilotPoints:
		print(callsign+", "+str(pilotPoints[callsign]))
	return pilotPoints

def slformat():
	resultsFile = getLatestResultsFile()
	raceResults = getRaceResults(resultsFile)
	rounds = calculateRoundPoints(raceResults)
	pilotTotalPoints = getPilotTotalsFromRounds(rounds)


slformat()

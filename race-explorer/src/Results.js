import React, { useState, useEffect } from 'react';
import './Results.css';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import Stack from '@mui/material/Stack';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import { TrackMapContainer, Map } from './TrackMap.js';
import * as util from './util.js';
import { createMqttConfigLoader, createTrackDataLoader, createTimerMappingLoader, createEventDataLoader, createResultDataLoader, getMqttClient } from './rh-client.js';

function processResults(data, raceEvents) {
  const jsonl = data.split('\n');
  for (const l of jsonl) {
    if (l.length > 0) {
      try {
        const msg = JSON.parse(l);
        processMessage(msg, raceEvents);
      } catch (ex) {
        console.log(ex+": "+l);
      }
    }
  }
}

function processMessage(msg, raceEvents) {
  if (!('event' in msg)) {
    return;
  }
  raceEvents[msg.event] = raceEvents[msg.event] ?? {};
  const event = raceEvents[msg.event];

  if (!('stage' in msg)) {
    return;
  }
  event[msg.stage] = event[msg.stage] ?? {};
  const stage = event[msg.stage];

  if (!('round' in msg)) {
    return;
  }
  stage[msg.round] = stage[msg.round] ?? {};
  const round = stage[msg.round];

  if (!('heat' in msg)) {
    return;
  }
  round[msg.heat] = round[msg.heat] ?? {pilots: {}, lastRaceUpdate: 0};
  const heat = round[msg.heat];

  if ('startTime' in msg) {
    heat.startTime = msg.startTime;
  }
  if ('finishTime' in msg) {
    heat.finishTime = msg.finishTime;
  }
  if ('stopTime' in msg) {
    heat.stopTime = msg.stopTime;
  }
  if ('pilot' in msg) {
    const pilots = heat.pilots;
    pilots[msg.pilot] = pilots[msg.pilot] ?? {name: msg.pilot, laps: []};
    const pilot = pilots[msg.pilot];
    if ('lap' in msg) {
      const lapData = {lap: msg.lap, timestamp: msg.timestamp, location: msg.location};
      pilot.laps.push(lapData);
    } else if ('laps' in msg) {
      pilot.laps.push(...msg['laps']);
    }
    if (pilot.laps.length > 0) {
      heat.lastRaceUpdate = Math.max(pilot.laps[pilot.laps.length-1].timestamp, heat.lastRaceUpdate);
    }
  }
}

function getRaceListener(setMqttData) {
  return (topic, payload) => {
    const parts = util.splitTopic(topic);
    const event = parts[parts.length-4];
    const stage = parts[parts.length-3];
    const heat = parts[parts.length-2];
    const round = parts[parts.length-1];
    const msg = JSON.parse(new TextDecoder('UTF-8').decode(payload));
    setMqttData((old) => [...old, {event, stage, heat, round, ...msg}]);
  };
}

function getLapListener(setMqttData) {
  return (topic, payload) => {
    const parts = util.splitTopic(topic);
    const event = parts[parts.length-7];
    const stage = parts[parts.length-6];
    const heat = parts[parts.length-5];
    const round = parts[parts.length-4];
    const pilot = parts[parts.length-3];
    const lap = Number(parts[parts.length-2]);
    const location = Number(parts[parts.length-1]);
    const msg = JSON.parse(new TextDecoder('UTF-8').decode(payload));
    setMqttData((old) => [...old, {event, stage, heat, round, pilot, lap, location, ...msg}]);
  };
}

const ID_PREFIX = 'id:';

function lookupByIndexOrId(arr, key) {
  if (key.startsWith(ID_PREFIX)) {
    const id = key.substring(ID_PREFIX.length);
    return arr?.find((v)=>v.id === id);
  } else {
    return arr?.[key];
  }
}
export default function Results(props) {
  const [mqttConfig, setMqttConfig] = useState({});
  const [trackData, setTrackData] = useState({});
  const [flyTo, setFlyTo] = useState(null);
  const [timerMapping, setTimerMapping] = useState([]);
  const [timedLocations, setTimedLocations] = useState([]);
  const [eventData, setEventData] = useState({});
  const [resultData, setResultData] = useState({});
  const [mqttRaceData, setMqttRaceData] = useState([]);
  const [mqttLapData, setMqttLapData] = useState([]);
  const [selectedEvent, setEvent] = useState('');
  const [selectedStage, setStage] = useState('');
  const [selectedRound, setRound] = useState('');
  const [selectedHeat, setHeat] = useState('');

  useEffect(() => {
    const loader = createMqttConfigLoader();
    loader.load(null, setMqttConfig);
    return () => loader.cancel();
  }, []);

  useEffect(() => {
    const loader = createTrackDataLoader();
    loader.load(null, (data) => {
      setTrackData(data);
      const startPos = data?.layout?.[0]?.location ?? [0,0];
      setFlyTo(startPos);
    });
    return () => loader.cancel();
  }, []);

  useEffect(() => {
    const loader = createTimerMappingLoader();
    loader.load(null, (data) => {
      setTimerMapping(data);
    });
    return () => loader.cancel();
  }, []);

  useEffect(() => {
    const loader = createEventDataLoader(selectedEvent);
    loader.load(null, (data) => {
      setEventData(data);
    });
    return () => loader.cancel();
  }, [selectedEvent]);

  useEffect(() => {
    if (trackData?.layout) {
      const mappedLocations = {};
      Object.entries(timerMapping).forEach((timerEntry) => {
        const timerId = timerEntry[0];
        Object.entries(timerEntry[1]).forEach((nmEntry) => {
          const nmId = nmEntry[0];
          Object.entries(nmEntry[1]).forEach((nEntry) => {
            const nId = nEntry[0];
            const n = nEntry[1];
            mappedLocations[n.location] = mappedLocations[n.location] ?? [];
            mappedLocations[n.location].push([timerId,nmId,nId]);
          })
        });
      });
      const timedLocIds = [];
      for (let locId=0; locId<trackData.layout.length; locId++) {
        if (mappedLocations[trackData.layout[locId].name]) {
          timedLocIds.push(locId);
        }
      }
      setTimedLocations(timedLocIds);
    }
  }, [trackData, timerMapping]);

  useEffect(() => {
    const loader = createResultDataLoader();
    loader.load(processResults, setResultData);
    return () => loader.cancel();
  }, []);

  useEffect(() => {
    if (mqttConfig?.raceAnnTopic) {
      const raceTopic = util.makeTopic(mqttConfig.raceAnnTopic, ['+', '+', '+', '+']);
      const mqttSubscriber = (setMqttData) => {
        const raceListener = getRaceListener(setMqttData);
        const mqttClient = getMqttClient();
        mqttClient.on('message', raceListener);
        mqttClient.subscribe(raceTopic);
        return () => {
          mqttClient.unsubscribe(raceTopic);
          mqttClient.off('message', raceListener);
          setMqttData([]);
        };
      };
      return mqttSubscriber(setMqttRaceData);
    }
  }, [mqttConfig]);

  useEffect(() => {
    if (mqttConfig?.raceAnnTopic && selectedEvent && selectedStage && selectedRound && selectedHeat) {
      const lapTopic = util.makeTopic(mqttConfig.raceAnnTopic, [selectedEvent, selectedStage, selectedHeat, selectedRound, '+', '+', '+']);
      const mqttSubscriber = (setMqttData) => {
        const lapListener = getLapListener(setMqttData);
        const mqttClient = getMqttClient();
        mqttClient.on('message', lapListener);
        mqttClient.subscribe(lapTopic);
        return () => {
          mqttClient.unsubscribe(lapTopic);
          mqttClient.off('message', lapListener);
          setMqttData([]);
        };
      };
      return mqttSubscriber(setMqttLapData);
    }
  }, [mqttConfig, selectedEvent, selectedStage, selectedRound, selectedHeat]);

  util.useInterval(() => {
    const loader = createResultDataLoader();
    loader.load(processResults, (data) => {
      setResultData(data);
      setMqttRaceData((old) => old.filter((msg) => !data?.[msg.event]?.[msg.stage]?.[msg.round]?.[msg.heat]?.stopTimestamp));
      setMqttLapData((old) => old.filter((msg) => msg.timestamp > data?.[msg.event]?.[msg.stage]?.[msg.round]?.[msg.heat]?.lastRaceUpdate));
    });
  }, 60000);

  const selectEvent = (event) => {
    setEvent(event);
  };

  const selectStage = (stage) => {
    setStage(stage);
  };

  const selectRound = (round) => {
    setRound(round);
  };

  const selectHeat = (heat) => {
    setHeat(heat);
  };

  for (const msg of mqttRaceData) {
    processMessage(msg, resultData);
  }
  for (const msg of mqttLapData) {
    processMessage(msg, resultData);
  }

  const eventNames = Object.keys(resultData);
  let stageData = {};
  let stageNames = [];
  let roundData = {};
  let roundIdxs = [];
  let heatData = {};
  let heatNames = [];
  let heat = {pilots: {}};
  if (selectedEvent in resultData) {
    stageData = resultData[selectedEvent];
    stageNames = Object.keys(stageData);
    if (selectedStage in stageData) {
      roundData = stageData[selectedStage];
      roundIdxs = Object.keys(roundData);
      if (selectedRound in roundData) {
        heatData = roundData[selectedRound];
        heatNames = Object.keys(heatData);
        if (selectedHeat in heatData) {
          heat = heatData[selectedHeat];
        } else {
          if (heatNames.length > 0) {
            setHeat(heatNames[heatNames.length-1]);
          }
        }
      } else {
        if (roundIdxs.length > 0) {
          setRound(roundIdxs[roundIdxs.length-1]);
        }
      }
    } else {
      if (stageNames.length > 0) {
        setStage(stageNames[stageNames.length-1]);
      }
    }
  } else {
    if (eventNames.length > 0) {
      setEvent(eventNames[eventNames.length-1]);
    }
  }

  const trackLayout = trackData.layout;
  let minLaps = Number.MAX_SAFE_INTEGER;
  let maxLaps = 0;
  const pilotLapDetails = {};
  const pilotPositions = {}
  for (const pilotHeat of Object.values(heat.pilots)) {
    const pilotLaps = pilotHeat.laps;
    const lapSplits = [];
    for (const lap of pilotLaps) {
      const lapNumber = lap['lap'];
      minLaps = Math.min(lapNumber, minLaps);
      maxLaps = Math.max(lapNumber, maxLaps);
      lapSplits[lap.lap] = lapSplits[lap.lap] ?? [];
      lapSplits[lap.lap][lap.location] = lap.timestamp;
    }
    pilotLapDetails[pilotHeat.name] = lapSplits;

    if (trackLayout) {
      const lastLocation = pilotLaps.length > 0 ? pilotLaps[pilotLaps.length-1].location : 0;
      const lastPosition = trackLayout[lastLocation].location;
      const nextPosition = trackLayout[lastLocation+1 < trackLayout.length ? lastLocation+1 : 0].location;
      const t = 0.5 + 0.25*(Math.random() - 0.5);
      const x = (t*nextPosition[0] + (1-t)*lastPosition[0]);
      const y = (t*nextPosition[1] + (1-t)*lastPosition[1]);
      pilotPositions[pilotHeat.name] = [x, y];
    }
  }

  const raceClassName = lookupByIndexOrId(lookupByIndexOrId(eventData.stages, selectedStage)?.races, selectedHeat)?.class;
  const raceFormatName = eventData.classes?.[raceClassName]?.format;
  const raceFormat = eventData.formats?.[raceFormatName];
  const lapCountOffset = raceFormat?.start === 'start-line' ? 1 : 0;
  let lapHeaders = [];
  for (let i=maxLaps; i>=minLaps; i--) {
    lapHeaders.push(<TableCell key={i} align="right">Lap {i+lapCountOffset}</TableCell>);
  }

  return (
    <Stack direction="column" alignItems="stretch">
      <Stack direction="row">
      <FormControl>
        <InputLabel id="event-label">Event</InputLabel>
        <Select labelId="event-label" sx={{minWidth: '6em'}} value={selectedEvent} onChange={(evt) => selectEvent(evt.target.value)}>
        {eventNames.map((name) => {
          return (
          <MenuItem key={name} value={name}>{name}</MenuItem>
          );
        })}
        </Select>
      </FormControl>
      <FormControl>
        <InputLabel id="stage-label">Stage</InputLabel>
        <Select labelId="stage-label" sx={{minWidth: '6em'}} value={selectedStage} onChange={(evt) => selectStage(evt.target.value)}>
        {stageNames.map((name) => {
          return (
          <MenuItem key={name} value={name}>{lookupByIndexOrId(eventData.stages, name)?.name ?? name}</MenuItem>
          );
        })}
        </Select>
      </FormControl>
      <FormControl>
        <InputLabel id="round-label">Round</InputLabel>
        <Select labelId="round-label" sx={{minWidth: '6em'}} value={selectedRound} onChange={(evt) => selectRound(evt.target.value)}>
        {roundIdxs.map((idx) => {
          return (
          <MenuItem key={idx} value={idx}>{Number(idx)+1}</MenuItem>
          );
        })}
        </Select>
      </FormControl>
      <FormControl>
        <InputLabel id="heat-label">Heat</InputLabel>
        <Select labelId="heat-label" sx={{minWidth: '5em'}} value={selectedHeat} onChange={(evt) => selectHeat(evt.target.value)}>
        {heatNames.map((name) => {
          return (
          <MenuItem key={name} value={name}>{lookupByIndexOrId(lookupByIndexOrId(eventData.stages, selectedStage)?.heats, name)?.name ?? name}</MenuItem>
          );
        })}
        </Select>
      </FormControl>
      </Stack>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell align="left">Pilot</TableCell>
              {lapHeaders}
            </TableRow>
          </TableHead>
          <TableBody>
          {Object.entries(pilotLapDetails).map((entry) => {
            const pilotKey = entry[0];
            const lapSplits = entry[1];
            let lapCells = [];
            for (let lapId=maxLaps; lapId>=minLaps; lapId--) {
              let lapInfo = [];
              if (lapSplits[lapId]) {
                const timestamps = lapSplits[lapId];
                for (const locId of timedLocations) {
                  let delta = null;
                  let timestamp = null;
                  if (locId === 0) {
                    if (timestamps[locId]) {
                      timestamp = timestamps[locId];
                      if (lapId === 0) {
                        delta = timestamp;
                      } else if (lapId > 0 && lapSplits[lapId-1]?.[0]) {
                        delta = timestamp - lapSplits[lapId-1][0];
                      }
                    }
                    lapInfo.push(
                      <div key={lapId+'/'+locId}>
                      <span className="lapTime">{delta !== null ? util.formatTimeMillis(delta) : '-'}</span>
                      <span> </span>
                      <span className="lapTimestamp">({timestamp !== null ? util.formatTimeMillis(timestamp) : '-'})</span>
                      </div>
                    );
                  } else if (locId > 0) {
                    if (timestamps[locId]) {
                      timestamp = timestamps[locId];
                      if (timestamps[locId-1]) {
                        delta = timestamp - timestamps[locId-1];
                      }
                    }
                    lapInfo.push(
                      <div key={lapId+'/'+locId}>
                      <span className="splitTime">{delta !== null ? util.formatTimeMillis(delta) : '-'}</span>
                      <span> </span>
                      <span className="splitTimestamp">({timestamp !== null ? util.formatTimeMillis(timestamp) : '-'})</span>
                      </div>
                    );
                  }
                }
                if (lapInfo.length > 1) {
                  // split between last gate and first gate
                  let delta = null;
                  let timestamp = null;
                  if (lapSplits[lapId+1]?.[0]) {
                    timestamp = lapSplits[lapId+1][0];
                    if (timestamps[timedLocations[timedLocations.length-1]]) {
                      delta = timestamp - timestamps[timedLocations[timedLocations.length-1]];
                    }
                  }
                  lapInfo.push(
                    <div key={lapId+':-1'}>
                    <span className="splitTime">{delta !== null ? util.formatTimeMillis(delta) : '-'}</span>
                    <span> </span>
                    <span className="splitTimestamp">({timestamp !== null ? util.formatTimeMillis(timestamp) : '-'})</span>
                    </div>
                  );
                }
              }
              lapCells.push(<TableCell key={lapId} align="right">{lapInfo}</TableCell>);
            }
            return (
            <TableRow
              key={pilotKey}
              sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
            >
              <TableCell component="th" scope="row">{pilotKey}</TableCell>
              {lapCells}
            </TableRow>
            );
          })}
          </TableBody>
        </Table>
      </TableContainer>
      <TrackMapContainer id="map" crs={trackData.crs} units={trackData.units} trackLayout={trackData.layout} pilotPositions={pilotPositions} flyTo={flyTo}/>
      <Map id="map"/>
    </Stack>
  );
}

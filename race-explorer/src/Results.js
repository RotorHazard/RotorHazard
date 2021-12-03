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
import * as util from './util.js';
import { createTrackDataLoader, createTimerMappingLoader, createResultDataLoader } from './rh-client.js';


function processResults(data, raceEvents) {
  const jsonl = data.split('\n');
  for (const l of jsonl) {
    if (l.length > 0) {
      try {
        const msg = JSON.parse(l);
        if ('event' in msg) {
          raceEvents[msg.event] = raceEvents[msg.event] ?? {};
          const event = raceEvents[msg.event];
          if ('round' in msg) {
            event[msg.round] = event[msg.round] ?? {};
            const round = event[msg.round];
            if ('heat' in msg) {
              round[msg.heat] = round[msg.heat] ?? {};
              const heat = round[msg.heat];
              if ('pilot' in msg) {
                heat[msg.pilot] = heat[msg.pilot] ?? {name: msg.pilot, laps: []};
                const pilot = heat[msg.pilot]
                if ('lap' in msg) {
                  const lapData = {lap: msg.lap, timestamp: msg.timestamp, location: msg.location};
                  pilot.laps.push(lapData);
                } else if ('laps' in msg) {
                  pilot.laps.push(...msg['laps']);
                }
              }
            }
          }
        }
      } catch (ex) {
        console.log(ex+": "+l);
      }
    }
  }
}

export default function Results(props) {
  const [trackData, setTrackData] = useState({});
  const [timerMapping, setTimerMapping] = useState([]);
  const [timedLocations, setTimedLocations] = useState([]);
  const [resultData, setResultData] = useState({});
  const [selectedEvent, setEvent] = useState('');
  const [selectedRound, setRound] = useState('');
  const [selectedHeat, setHeat] = useState('');

  useEffect(() => {
    const loader = createTrackDataLoader();
    loader.load(null, (data) => {
      setTrackData(data);
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

  util.useInterval(() => {
    const loader = createResultDataLoader();
    loader.load(processResults, setResultData);
  }, 60000);

  const selectEvent = (event) => {
    setEvent(event);
  };

  const selectRound = (round) => {
    setRound(round);
  };

  const selectHeat = (heat) => {
    setHeat(heat);
  };

  const eventNames = Object.keys(resultData);
  let roundData = {};
  let roundNames = [];
  let heatData = {};
  let heatNames = [];
  let pilotHeatData = {};
  if (selectedEvent in resultData) {
    roundData = resultData[selectedEvent];
    roundNames = Object.keys(roundData);
    if (selectedRound in roundData) {
      heatData = roundData[selectedRound];
      heatNames = Object.keys(heatData);
      if (selectedHeat in heatData) {
        pilotHeatData = heatData[selectedHeat];
      } else {
        if (heatNames.length > 0) {
          setHeat(heatNames[heatNames.length-1]);
        }
      }
    } else {
      if (roundNames.length > 0) {
        setRound(roundNames[roundNames.length-1]);
      }
    }
  } else {
    if (eventNames.length > 0) {
      setEvent(eventNames[eventNames.length-1]);
    }
  }

  let minLaps = Number.MAX_SAFE_INTEGER;
  let maxLaps = 0;
  for (const pilotHeat of Object.values(pilotHeatData)) {
    for (const lap of pilotHeat.laps) {
      const lapNumber = lap['lap'];
      minLaps = Math.min(lapNumber, minLaps);
      maxLaps = Math.max(lapNumber, maxLaps);
    }
  }

  let lapHeaders = [];
  for (let i=maxLaps; i>=minLaps; i--) {
    lapHeaders.push(<TableCell key={i} align="right">Lap {i}</TableCell>);
  }

  return (
    <Stack direction="column" alignItems="stretch">
      <FormControl>
        <InputLabel id="event-label">Event</InputLabel>
        <Select labelId="event-label" value={selectedEvent} onChange={(evt) => selectEvent(evt.target.value)}>
        {eventNames.map((name) => {
          return (
          <MenuItem key={name} value={name}>{name}</MenuItem>
          );
        })}
        </Select>
      </FormControl>
      <FormControl>
        <InputLabel id="round-label">Round</InputLabel>
        <Select labelId="round-label" value={selectedRound} onChange={(evt) => selectRound(evt.target.value)}>
        {roundNames.map((name) => {
          return (
          <MenuItem key={name} value={name}>{name}</MenuItem>
          );
        })}
        </Select>
      </FormControl>
      <FormControl>
        <InputLabel id="heat-label">Heat</InputLabel>
        <Select labelId="heat-label" value={selectedHeat} onChange={(evt) => selectHeat(evt.target.value)}>
        {heatNames.map((name) => {
          return (
          <MenuItem key={name} value={name}>{name}</MenuItem>
          );
        })}
        </Select>
      </FormControl>
      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell align="left">Pilot</TableCell>
              {lapHeaders}
            </TableRow>
          </TableHead>
          <TableBody>
          {Object.entries(pilotHeatData).map((entry) => {
            const pilotKey = entry[0];
            const pilotHeat = entry[1];
            const laps = [];
            for (const lap of pilotHeat.laps) {
              laps[lap.lap] = laps[lap.lap] ?? [];
              laps[lap.lap][lap.location] = lap.timestamp;
            }
            let lapCells = [];
            for (let lapId=maxLaps; lapId>=minLaps; lapId--) {
              let lapInfo = [];
              if (laps[lapId]) {
                const timestamps = laps[lapId];
                for (const locId of timedLocations) {
                  let delta = null;
                  let timestamp = null;
                  if (locId === 0) {
                    if (timestamps[locId]) {
                      timestamp = timestamps[locId];
                      if (lapId === 0) {
                        delta = timestamp;
                      } else if (lapId > 0 && laps[lapId-1]?.[0]) {
                        delta = timestamp - laps[lapId-1][0];
                      }
                    }
                    lapInfo.push(
                      <div>
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
                      <div>
                      <span className="splitTime">{delta !== null ? util.formatTimeMillis(delta) : '-'}</span>
                      <span> </span>
                      <span className="splitTimestamp">({timestamp !== null ? util.formatTimeMillis(timestamp) : '-'})</span>
                      </div>
                    );
                  }
                }
                let delta = null;
                let timestamp = null;
                if (laps[lapId+1]?.[0]) {
                  timestamp = laps[lapId+1][0];
                  if (timestamps[timedLocations[timedLocations.length-1]]) {
                    delta = timestamp - timestamps[timedLocations[timedLocations.length-1]];
                  }
                }
                lapInfo.push(
                  <div>
                  <span className="splitTime">{delta !== null ? util.formatTimeMillis(delta) : '-'}</span>
                  <span> </span>
                  <span className="splitTimestamp">({timestamp !== null ? util.formatTimeMillis(timestamp) : '-'})</span>
                  </div>
                );
              }
              lapCells.push(<TableCell key={lapId} align="right">{lapInfo}</TableCell>);
            }
            return (
            <TableRow
              key={pilotKey}
              sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
            >
              <TableCell component="th" scope="row">{pilotHeat.name}</TableCell>
              {lapCells}
            </TableRow>
            );
          })}
          </TableBody>
        </Table>
      </TableContainer>
    </Stack>
  );
}

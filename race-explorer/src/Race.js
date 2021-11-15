import React, { useState, useEffect, useRef } from 'react';
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
import createLoader from './rh-client.js';


function processEvents(eventData, raceEvents) {
  const jsonl = eventData.split('\n');
  for (const l of jsonl) {
    if (l.length > 0) {
      try {
        const msg = JSON.parse(l);
        if ('event' in msg) {
          raceEvents[msg.event] = raceEvents[msg.event] ?? {};
          let event = raceEvents[msg.event];
          if ('round' in msg) {
            event[msg.round] = event[msg.round] ?? {};
            let round = event[msg.round];
            if ('heat' in msg) {
              round[msg.heat] = round[msg.heat] ?? {};
              let heat = round[msg.heat];
              if ('pilot' in msg) {
                heat[msg.pilot] = heat[msg.pilot] ?? {pilot: msg.pilot, laps: []};
                let pilot = heat[msg.pilot]
                if ('lap' in msg) {
                  pilot.laps.push({lap: msg.lap, timestamp: msg.timestamp, gate: msg.gate});
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

async function readData(loader, setEventData) {
  try {
    let raceEvents = {};
    await loader(processEvents, raceEvents);
    setEventData(raceEvents);
  } catch (err) {
    console.log(err);
  }
}

export default function Race(props) {
  const [eventData, setEventData] = useState({});
  const [selectedEvent, setEvent] = useState('');
  const [selectedRound, setRound] = useState('');
  const [selectedHeat, setHeat] = useState('');
  const loaderRef = useRef();

  useEffect(() => {
    const loader = createLoader();
    loaderRef.current = loader;
    readData(loader, setEventData);
  }, []);

  util.useInterval(() => {readData(loaderRef.current, setEventData);}, 60000);

  const selectEvent = (event) => {
    setEvent(event);
  };

  const selectRound = (round) => {
    setRound(round);
  };

  const selectHeat = (heat) => {
    setHeat(heat);
  };

  const eventNames = Object.keys(eventData);
  let roundData = {};
  let roundNames = [];
  let heatData = {};
  let heatNames = [];
  let pilotHeatData = {};
  if (selectedEvent in eventData) {
    roundData = eventData[selectedEvent];
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
        <Select labelId="event-label" label="Event" value={selectedEvent} onChange={(evt) => selectEvent(evt.target.value)}>
        {eventNames.map((name) => {
          return (
          <MenuItem key={name} value={name}>{name}</MenuItem>
          );
        })}
        </Select>
      </FormControl>
      <FormControl>
        <InputLabel id="round-label">Round</InputLabel>
        <Select labelId="round-label" label="Round" value={selectedRound} onChange={(evt) => selectRound(evt.target.value)}>
        {roundNames.map((name) => {
          return (
          <MenuItem key={name} value={name}>{name}</MenuItem>
          );
        })}
        </Select>
      </FormControl>
      <FormControl>
        <InputLabel id="heat-label">Heat</InputLabel>
        <Select labelId="heat-label" label="Heat" value={selectedHeat} onChange={(evt) => selectHeat(evt.target.value)}>
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
            let lapCells = [];
            let k = pilotHeat.laps.length - 1;
            for (let i=maxLaps; i>=minLaps; i--) {
              let lapInfo = [];
              if (i === pilotHeat.laps[k].lap) {
                if (k-1 >= 0 && i-1 === pilotHeat.laps[k-1].lap) {
                  lapInfo.push(util.formatTimeMillis(pilotHeat.laps[k].timestamp-pilotHeat.laps[k-1].timestamp)+'\n');
                }
                lapInfo.push(<span class='lapTimestamp'>({util.formatTimeMillis(pilotHeat.laps[k].timestamp)})</span>);
                k--;
              }
              lapCells.push(<TableCell key={i} align="right">{lapInfo}</TableCell>);
            }
            return (
            <TableRow
              key={pilotKey}
              sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
            >
              <TableCell component="th" scope="row">{pilotHeat.pilot}</TableCell>
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

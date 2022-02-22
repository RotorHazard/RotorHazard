import React, { useState, useEffect } from 'react';
import FormControl from '@mui/material/FormControl';
import MenuItem from '@mui/material/MenuItem';
import InputAdornment from '@mui/material/InputAdornment';
import InputLabel from '@mui/material/InputLabel';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Select from '@mui/material/Select';
import TextField from '@mui/material/TextField';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import ComputerIcon from '@mui/icons-material/Computer';
import DeveloperBoardIcon from '@mui/icons-material/DeveloperBoard';
import MemoryIcon from '@mui/icons-material/Memory';
import EventSeatIcon from '@mui/icons-material/EventSeat';
import FlagIcon from '@mui/icons-material/Flag';
import { debounce } from 'lodash';
import { processVtxTable } from './Frequency.js';
import RHNodeConfigFactory from './RotorHazard.js';
import LapRFNodeConfigFactory from './LapRF.js';
import * as util from './util.js';
import { createSetupDataLoader, createVtxTableLoader, createTimerMappingLoader, storeTimerMapping, createTrackDataLoader, createMqttConfigLoader } from './rh-client.js';

function processSetup(data, setupData) {
  const jsonl = data.split('\n');
  for (const l of jsonl) {
    if (l.length > 0) {
      try {
        const msg = JSON.parse(l);
        if ('timer' in msg) {
          setupData[msg.timer] = setupData[msg.timer] ?? {};
          const timer = setupData[msg.timer];
          if ('nodeManager' in msg) {
            timer[msg.nodeManager] = timer[msg.nodeManager] ?? {type: '', nodes: {}};
            const nm = timer[msg.nodeManager];
            if ('type' in msg) {
              nm.type = msg.type;
            }
            if ('node' in msg) {
              nm.nodes[msg.node] = nm.nodes[msg.node] ?? {};
              const node = nm.nodes[msg.node];
              if ('frequency' in msg) {
                node.frequency = msg.frequency;
              }
              if ('bandChannel' in msg) {
                node.bandChannel = msg.bandChannel;
              }
              if ('enterTrigger' in msg) {
                node.enterTrigger = msg.enterTrigger;
              }
              if ('exitTrigger' in msg) {
                node.exitTrigger = msg.exitTrigger;
              }
              if ('threshold' in msg) {
                node.threshold = msg.threshold;
              }
              if ('gain' in msg) {
                node.gain = msg.gain;
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

function getTimerConfigFactory(type) {
  if (type === 'LapRF') {
    return LapRFNodeConfigFactory;
  } else {
    return RHNodeConfigFactory;
  }
}

function TrackConfig(props) {
  const {location: givenLocation, seat: givenSeat,
    onLocationChange, onSeatChange,
    trackLayout} = props;
  const [location, setLocation] = useState(givenLocation ?? 'Start/finish');
  const [seat, setSeat] = useState(givenSeat ?? 0);

  useEffect(() => {
    setLocation(givenLocation ?? 'Start/finish');
  }, [givenLocation]);


  useEffect(() => {
    setSeat(givenSeat ?? 0);
  }, [givenSeat]);

  const changeLocation = (v) => {
    setLocation(v);
    if (onLocationChange) {
      onLocationChange(v);
    }
  };

  const changeSeat = (s) => {
    setSeat(s);
    if (onSeatChange) {
      onSeatChange(s);
    }
  };

  return (
    <div>
    <FormControl>
    <InputLabel id="location-label">Track location</InputLabel>
    <Select labelId="location-label" value={location} defaultValue=""
      onChange={(evt) => changeLocation(evt.target.value)}>
      {
        trackLayout.map((loc) => {
          return (
            <MenuItem key={loc.name} value={loc.name}>
              <ListItemIcon><FlagIcon/></ListItemIcon>
              <ListItemText>{loc.name}</ListItemText>
             </MenuItem>
          );
        })
      }
    </Select>
    </FormControl>
    <TextField label="Seat" value={seat+1}
      onChange={(evt) => changeSeat(evt.target.value-1)}
      inputProps={{
      step: 1,
      min: 1,
      type: 'number'
      }}
      InputProps={{
        startAdornment: <InputAdornment position="start"><EventSeatIcon/></InputAdornment>
      }}
    />
    </div>
  );
}

const saveTimerMapping = debounce(storeTimerMapping, 2000);

export default function Setup(props) {
  const [mqttConfig, setMqttConfig] = useState({});
  const [vtxTable, setVtxTable] = useState({});
  const [trackLayout, setTrackLayout] = useState([]);
  const [timerMapping, setTimerMapping] = useState([]);
  const [setupData, setSetupData] = useState({});

  useEffect(() => {
    const loader = createMqttConfigLoader();
    loader.load(null, setMqttConfig);
    return () => loader.cancel();
  }, []);

  useEffect(() => {
    const loader = createVtxTableLoader();
    loader.load(processVtxTable, setVtxTable);
    return () => loader.cancel();
  }, []);

  useEffect(() => {
    const loader = createTrackDataLoader();
    loader.load(null, (data) => {
      setTrackLayout(data.layout);
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
    const loader = createSetupDataLoader();
    loader.load(processSetup, setSetupData);
    return () => loader.cancel();
  }, []);

  useEffect(() => {
    saveTimerMapping(timerMapping);
  }, [timerMapping]);

  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Timer</TableCell>
            <TableCell>Node manager</TableCell>
            <TableCell>Node</TableCell>
            <TableCell>Setup</TableCell>
            <TableCell>Track</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
        {
          Object.entries(setupData).map((timerEntry) => {
            const timerId = timerEntry[0];
            const nodeManagers = Object.entries(timerEntry[1]);
            let timerCell = <TableCell rowSpan={nodeManagers.length}><ComputerIcon/>{timerId}</TableCell>;
            return nodeManagers.map((nmEntry) => {
              const nmAddr = nmEntry[0];
              const nm = nmEntry[1];
              const nodes = Object.entries(nm.nodes);
              let nmCell = <TableCell rowSpan={nodes.length}><DeveloperBoardIcon/>{nmAddr}</TableCell>;
              const createNodeConfig = getTimerConfigFactory(nm.type);
              return nodes.map((nodeEntry) => {
                const nodeIdx = nodeEntry[0];
                const nodeData = nodeEntry[1];
                const annTopic = mqttConfig ? util.makeTopic(mqttConfig.timerAnnTopic, [timerId, nmAddr, nodeIdx]) : null;
                const ctrlTopic = mqttConfig ? util.makeTopic(mqttConfig.timerCtrlTopic, [timerId, nmAddr, nodeIdx]) : null;
                const node = {...nodeData, timer: timerId, address: nmAddr, index: nodeIdx};
                const nodeConfig = createNodeConfig(node, vtxTable, annTopic, ctrlTopic);
                const firstCell = timerCell;
                timerCell = null;
                const secondCell = nmCell;
                nmCell = null;
                const trackLocation = timerMapping[timerId]?.[nmAddr]?.[nodeIdx]?.location;
                const seat = timerMapping[timerId]?.[nmAddr]?.[nodeIdx]?.seat;
                const updateLocation = (loc) => {
                  const mappingInfo = timerMapping[timerId] ?? {};
                  mappingInfo[nmAddr] = mappingInfo[nmAddr] ?? [];
                  mappingInfo[nmAddr][nodeIdx] = mappingInfo[nmAddr][nodeIdx] ?? {};
                  mappingInfo[nmAddr][nodeIdx].location = loc;
                  setTimerMapping({...timerMapping, [timerId]: mappingInfo});
                };
                const updateSeat = (s) => {
                  const mappingInfo = timerMapping[timerId] ?? {};
                  mappingInfo[nmAddr] = mappingInfo[nmAddr] ?? [];
                  mappingInfo[nmAddr][nodeIdx] = mappingInfo[nmAddr][nodeIdx] ?? {};
                  mappingInfo[nmAddr][nodeIdx].seat = s;
                  setTimerMapping({...timerMapping, [timerId]: mappingInfo});
                };
                return (
                  <TableRow key={nodeIdx}>
                  {firstCell}
                  {secondCell}
                  <TableCell><MemoryIcon/>{nodeIdx}</TableCell>
                  <TableCell>{nodeConfig}</TableCell>
                  <TableCell>
                    <TrackConfig location={trackLocation} seat={seat} trackLayout={trackLayout}
                    onLocationChange={updateLocation} onSeatChange={updateSeat}/>
                  </TableCell>
                  </TableRow>
                );
              });
            });
          })
        }
        </TableBody>
      </Table>
    </TableContainer>
  );
}

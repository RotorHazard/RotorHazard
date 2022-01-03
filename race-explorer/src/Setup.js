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
import Frequency, { processVtxTable } from './Frequency.js';
import LapRFConfig from './LapRF.js';
import * as util from './util.js';
import { createSetupDataLoader, createVtxTableLoader, createTimerMappingLoader, storeTimerMapping, createTrackDataLoader, createMqttConfigLoader, getMqttClient } from './rh-client.js';

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
              nm.nodes[msg.node] = nm.nodes[msg.node] ?? {id: msg.node};
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

function EnterExitTriggers(props) {
  const {enterTrigger: givenEnterTrigger, exitTrigger: givenExitTrigger,
    enterTriggerChangesHook, exitTriggerChangesHook,
    onEnterTriggerChange, onExitTriggerChange} = props;
  const [enterTrigger, setEnterTrigger] = useState(givenEnterTrigger);
  const [exitTrigger, setExitTrigger] = useState(givenExitTrigger);

  useEffect(() => {
    setEnterTrigger(givenEnterTrigger);
  }, [givenEnterTrigger]);

  useEffect(() => {
    setExitTrigger(givenExitTrigger);
  }, [givenExitTrigger]);

  useEffect(() => {
    if (enterTriggerChangesHook) {
      return enterTriggerChangesHook((level) => {setEnterTrigger(level);});
    }
  }, [enterTriggerChangesHook]);

  useEffect(() => {
    if (exitTriggerChangesHook) {
      return exitTriggerChangesHook((level) => {setExitTrigger(level);});
    }
  }, [exitTriggerChangesHook]);

  const changeEnterTrigger = (level) => {
    setEnterTrigger(level);
    if (onEnterTriggerChange) {
      onEnterTriggerChange(level);
    }
  };

  const changeExitTrigger = (level) => {
    setExitTrigger(level);
    if (onExitTriggerChange) {
      onExitTriggerChange(level);
    }
  };

  return (
    <div>
    <TextField label="Enter trigger" value={enterTrigger}
      onChange={(evt) => changeEnterTrigger(evt.target.value)}
      inputProps={{
      step: 1,
      min: 0,
      max: 255,
      type: 'number'
    }}/>
    <TextField label="Exit trigger" value={exitTrigger}
      onChange={(evt) => changeExitTrigger(evt.target.value)}
      inputProps={{
      step: 1,
      min: 0,
      max: 255,
      type: 'number'
    }}/>
    </div>
  );
}

function TimerConfig(props) {
  const {node, annTopic, ctrlTopic, vtxTable} = props;

  const freq = node.frequency;
  const bc = node?.bandChannel ?? null;
  const enterTrigger = node.enterTrigger;
  const exitTrigger = node.exitTrigger;
  
  let mqttFrequencyPublisher = null;
  let mqttFrequencySubscriber = null;
  let mqttBandChannelSubscriber = null;
  let mqttEnterTriggerPublisher = null;
  let mqttEnterTriggerSubscriber = null;
  let mqttExitTriggerPublisher = null;
  let mqttExitTriggerSubscriber = null;
  if (annTopic && ctrlTopic) {
    const freqAnnTopic = [annTopic, "frequency"].join('/');
    const freqCtrlTopic = [ctrlTopic, "frequency"].join('/');
    const bcAnnTopic = [annTopic, "bandChannel"].join('/');
    const bcCtrlTopic = [ctrlTopic, "bandChannel"].join('/');
    mqttFrequencyPublisher = debounce((freq, bc) => {
      getMqttClient().publish(bcCtrlTopic, bc);
      getMqttClient().publish(freqCtrlTopic, freq+','+bc);
     }, 1500);
    mqttFrequencySubscriber = (setFreq) => {
      const mqttClient = getMqttClient();
      mqttClient.subscribeTo(freqAnnTopic, (payload) => {
        const newFreq = new TextDecoder('UTF-8').decode(payload);
        setFreq(newFreq);
      });
      return () => {
        mqttClient.unsubscribeFrom(freqAnnTopic);
      };
    };
    mqttBandChannelSubscriber = (setBandChannel) => {
      const mqttClient = getMqttClient();
      mqttClient.subscribeTo(bcAnnTopic, (payload) => {
        const newBandChannel = new TextDecoder('UTF-8').decode(payload);
        setBandChannel(newBandChannel);
      });
      return () => {
        mqttClient.unsubscribeFrom(bcAnnTopic);
      };
    };

    const enterTrigAnnTopic = [annTopic, "enterTrigger"].join('/');
    const enterTrigCtrlTopic = [ctrlTopic, "enterTrigger"].join('/');
    mqttEnterTriggerPublisher = (level) => {getMqttClient().publish(enterTrigCtrlTopic, level);};
    mqttEnterTriggerSubscriber = (setEnterTrigger) => {
      const mqttClient = getMqttClient();
      mqttClient.subscribeTo(enterTrigAnnTopic, (payload) => {
        const newLevel = new TextDecoder('UTF-8').decode(payload);
        setEnterTrigger(newLevel);
      });
      return () => {
        mqttClient.unsubscribeFrom(enterTrigAnnTopic);
      };
    };

    const exitTrigAnnTopic = [annTopic, "exitTrigger"].join('/');
    const exitTrigCtrlTopic = [ctrlTopic, "exitTrigger"].join('/');
    mqttExitTriggerPublisher = (level) => {getMqttClient().publish(exitTrigCtrlTopic, level);};
    mqttExitTriggerSubscriber = (setExitTrigger) => {
      const mqttClient = getMqttClient();
      mqttClient.subscribeTo(exitTrigAnnTopic, (payload) => {
        const newLevel = new TextDecoder('UTF-8').decode(payload);
        setExitTrigger(newLevel);
      });
      return () => {
        mqttClient.unsubscribeFrom(exitTrigAnnTopic);
      };
    };
  }
  
  return (
    <div>
    <Frequency frequency={freq.toString()} bandChannel={bc}
      onChange={mqttFrequencyPublisher}
      frequencyChangesHook={mqttFrequencySubscriber}
      bandChannelChangesHook={mqttBandChannelSubscriber}
      vtxTable={vtxTable}
    />
    <EnterExitTriggers enterTrigger={enterTrigger.toString()} exitTrigger={exitTrigger.toString()}
      onEnterTriggerChange={mqttEnterTriggerPublisher}
      enterTriggerChangesHook={mqttEnterTriggerSubscriber}
      onExitTriggerChange={mqttExitTriggerPublisher}
      exitTriggerChangesHook={mqttExitTriggerSubscriber}
    />
    </div>
  );
}

function getTimerConfigFactory(type) {
  if (type === 'LapRF') {
    return (node, vtxTable, annTopic, ctrlTopic) => <LapRFConfig node={node} vtxTable={vtxTable} annTopic={annTopic} ctrlTopic={ctrlTopic}/>;
  } else {
    return (node, vtxTable, annTopic, ctrlTopic) => <TimerConfig node={node} vtxTable={vtxTable} annTopic={annTopic} ctrlTopic={ctrlTopic}/>;
  }
}

function TrackConfig(props) {
  const {location: givenLocation, seat: givenSeat,
    onLocationChange, onSeatChange,
    trackLayout} = props;
  const [location, setLocation] = useState(givenLocation ?? 'Start/finish');
  const [seat, setSeat] = useState(givenSeat ?? 0);

  useEffect(() => {
    setLocation(givenLocation);
  }, [givenLocation]);


  useEffect(() => {
    setSeat(givenSeat);
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
              const createTimerConfig = getTimerConfigFactory(nm.type);
              return nodes.map((nodeEntry) => {
                const nodeId = nodeEntry[0];
                const node = nodeEntry[1];
                const annTopic = mqttConfig ? util.makeTopic(mqttConfig.timerAnnTopic, [timerId, nmAddr, nodeId]) : null;
                const ctrlTopic = mqttConfig ? util.makeTopic(mqttConfig.timerCtrlTopic, [timerId, nmAddr, nodeId]) : null;
                const timerConfig = createTimerConfig(node, vtxTable, annTopic, ctrlTopic);
                const firstCell = timerCell;
                timerCell = null;
                const secondCell = nmCell;
                nmCell = null;
                const trackLocation = timerMapping[timerId]?.[nmAddr]?.[nodeId]?.location;
                const seat = timerMapping[timerId]?.[nmAddr]?.[nodeId]?.seat;
                const updateLocation = (loc) => {
                  const mappingInfo = timerMapping[timerId] ?? {};
                  mappingInfo[nmAddr] = mappingInfo[nmAddr] ?? [];
                  mappingInfo[nmAddr][nodeId] = mappingInfo[nmAddr][nodeId] ?? {};
                  mappingInfo[nmAddr][nodeId].location = loc;
                  setTimerMapping({...timerMapping, [timerId]: mappingInfo});
                };
                const updateSeat = (s) => {
                  const mappingInfo = timerMapping[timerId] ?? {};
                  mappingInfo[nmAddr] = mappingInfo[nmAddr] ?? [];
                  mappingInfo[nmAddr][nodeId] = mappingInfo[nmAddr][nodeId] ?? {};
                  mappingInfo[nmAddr][nodeId].seat = s;
                  setTimerMapping({...timerMapping, [timerId]: mappingInfo});
                };
                return (
                  <TableRow key={nodeId}>
                  {firstCell}
                  {secondCell}
                  <TableCell><MemoryIcon/>{node.id}</TableCell>
                  <TableCell>{timerConfig}</TableCell>
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

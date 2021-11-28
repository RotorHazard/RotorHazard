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
import Frequency from './Frequency.js';
import LapRFConfig from './LapRF.js';
import { createSetupDataLoader, loadVtxTable, loadTrackData, loadMqttConfig, getMqttClient } from './rh-client.js';


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

async function readData(loader, setSetupData) {
  try {
    let setupData = {};
    await loader(processSetup, setupData);
    setSetupData(setupData);
  } catch (err) {
    console.log(err);
  }
}

function EnterExitTriggers(props) {
  const [enterTrigger, setEnterTrigger] = useState(props.enterTrigger);
  const [exitTrigger, setExitTrigger] = useState(props.exitTrigger);

  const enterTriggerChangesHook = props?.enterTriggerChangesHook;
  useEffect(() => {
    if (enterTriggerChangesHook) {
      return enterTriggerChangesHook((level) => {setEnterTrigger(level);});
    }
  }, [enterTriggerChangesHook]);

  const exitTriggerChangesHook = props?.exitTriggerChangesHook;
  useEffect(() => {
    if (exitTriggerChangesHook) {
      return exitTriggerChangesHook((level) => {setExitTrigger(level);});
    }
  }, [exitTriggerChangesHook]);

  const changeEnterTrigger = (level) => {
    setEnterTrigger(level);
    if (props?.onEnterTriggerChange) {
      props.onEnterTriggerChange(level);
    }
  };

  const changeExitTrigger = (level) => {
    setExitTrigger(level);
    if (props?.onExitTriggerChange) {
      props.onExitTriggerChange(level);
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
  const node = props.node;
  const freq = node.frequency;
  const bc = node?.bandChannel ?? null;
  const enterTrigger = node.enterTrigger;
  const exitTrigger = node.exitTrigger;
  
  let mqttFrequencyPublisher = null;
  let mqttFrequencySubscriber = null;
  let mqttBandChannelPublisher = null;
  let mqttBandChannelSubscriber = null;
  let mqttEnterTriggerPublisher = null;
  let mqttEnterTriggerSubscriber = null;
  let mqttExitTriggerPublisher = null;
  let mqttExitTriggerSubscriber = null;
  if (props.annTopic && props.ctrlTopic) {
    const freqAnnTopic = [props.annTopic, "frequency"].join('/');
    const freqCtrlTopic = [props.ctrlTopic, "frequency"].join('/');
    mqttFrequencyPublisher = debounce((freq) => {
      getMqttClient().publish(freqCtrlTopic, freq);
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
  
    const bcAnnTopic = [props.annTopic, "bandChannel"].join('/');
    const bcCtrlTopic = [props.ctrlTopic, "bandChannel"].join('/');
    mqttBandChannelPublisher = (bc) => {getMqttClient().publish(bcCtrlTopic, bc);};
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

    const enterTrigAnnTopic = [props.annTopic, "enterTrigger"].join('/');
    const enterTrigCtrlTopic = [props.ctrlTopic, "enterTrigger"].join('/');
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

    const exitTrigAnnTopic = [props.annTopic, "exitTrigger"].join('/');
    const exitTrigCtrlTopic = [props.ctrlTopic, "exitTrigger"].join('/');
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
      onFrequencyChange={mqttFrequencyPublisher}
      frequencyChangesHook={mqttFrequencySubscriber}
      onBandChannelChange={mqttBandChannelPublisher}
      bandChannelChangesHook={mqttBandChannelSubscriber}
      vtxTable={props.vtxTable}
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
  const [location, setLocation] = useState(props.location);
  const [seat, setSeat] = useState(props.seat);

  const changeLocation = (v) => {
    setLocation(v);
  };

  const changeSeat = (s) => {
    setSeat(s);
  };

  return (
    <div>
    <FormControl>
    <InputLabel id="location-label">Track location</InputLabel>
    <Select labelId="location-label" value={location}
      onChange={(evt) => changeLocation(evt.target.value)}>
      {
        props.trackLayout.map((loc) => {
          return (
            <MenuItem value={loc.name}>
              <ListItemIcon><FlagIcon/></ListItemIcon>
              <ListItemText>{loc.name}</ListItemText>
             </MenuItem>
          );
        })
      }
    </Select>
    </FormControl>
    <TextField label="Seat" value={seat}
      onChange={(evt) => changeSeat(evt.target.value)}
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

export default function Setup(props) {
  const [mqttConfig, setMqttConfig] = useState({});
  const [vtxTable, setVtxTable] = useState({});
  const [trackLayout, setTrackLayout] = useState([]);
  const [setupData, setSetupData] = useState({});

  useEffect(() => {
    loadMqttConfig(setMqttConfig);
  }, []);

  useEffect(() => {
    loadVtxTable(setVtxTable);
  }, []);

  useEffect(() => {
    loadTrackData((data) => {
      setTrackLayout(data.layout);
    });
  }, []);

  useEffect(() => {
    const loader = createSetupDataLoader();
    readData(loader, setSetupData);
  }, []);

  let trackLocationIdx = 0;
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
            const trackLocation = trackLayout[trackLocationIdx].name;
            trackLocationIdx++;
            let seat = 0;
            return nodeManagers.map((nmEntry) => {
              const nmAddr = nmEntry[0];
              const nm = nmEntry[1];
              const nodes = Object.entries(nm.nodes);
              let nmCell = <TableCell rowSpan={nodes.length}><DeveloperBoardIcon/>{nmAddr}</TableCell>;
              const createTimerConfig = getTimerConfigFactory(nm.type);
              return nodes.map((nodeEntry) => {
                const nodeId = nodeEntry[0];
                const node = nodeEntry[1];
                const annTopic = mqttConfig ? [mqttConfig.timerAnnTopic, timerId, nmAddr, nodeId].join('/') : null;
                const ctrlTopic = mqttConfig ? [mqttConfig.timerCtrlTopic, timerId, nmAddr, nodeId].join('/') : null;
                const timerConfig = createTimerConfig(node, vtxTable, annTopic, ctrlTopic);
                const firstCell = timerCell;
                timerCell = null;
                const secondCell = nmCell;
                nmCell = null;
                seat++;
                return (
                  <TableRow key={nodeId}>
                  {firstCell}
                  {secondCell}
                  <TableCell><MemoryIcon/>{node.id}</TableCell>
                  <TableCell>{timerConfig}</TableCell>
                  <TableCell><TrackConfig location={trackLocation} seat={seat} trackLayout={trackLayout}/></TableCell>
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

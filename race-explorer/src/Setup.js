import React, { useState, useEffect } from 'react';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import MenuItem from '@mui/material/MenuItem';
import Input from '@mui/material/Input';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import Tooltip from '@mui/material/Tooltip';
import ComputerIcon from '@mui/icons-material/Computer';
import DeveloperBoardIcon from '@mui/icons-material/DeveloperBoard';
import EventSeatIcon from '@mui/icons-material/EventSeat';
import FlagIcon from '@mui/icons-material/Flag';
import { debounce } from 'lodash';
import { createSetupDataLoader, loadVtxTable, loadMqttConfig, getMqttClient } from './rh-client.js';


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
              if ('enterTrigger in msg') {
                node.enterTrigger = msg.enterTrigger;
              }
              if ('exitTrigger in msg') {
                node.exitTrigger = msg.exitTrigger;
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

function Frequency(props) {
  const [frequency, setFrequency] = useState(props.frequency);
  const [band, setBand] = useState(props?.bandChannel?.[0] ?? '');
  const [channel, setChannel] = useState(props?.bandChannel?.[1] ?? '');
  const vtxTable = props.vtxTable;

  const frequencyChangesHook = props?.frequencyChangesHook;
  useEffect(() => {
    if (frequencyChangesHook) {
      return frequencyChangesHook((freq) => {setFrequency(freq); setBand(''); setChannel('');});
    }
  }, [frequencyChangesHook]);

  const bandChannelChangesHook = props?.bandChannelChangesHook;
  useEffect(() => {
    if (bandChannelChangesHook) {
      return bandChannelChangesHook((bandChannel) => {setBand(bandChannel[0]); setChannel(bandChannel[1]);});
    }
  }, [bandChannelChangesHook]);

  const changeFrequency = (frequency) => {
    setFrequency(frequency);
    setBand('');
    setChannel('');
    if (props?.onFrequencyChange) {
      props.onFrequencyChange(frequency);
    }
  };

  const selectBand = (band) => {
    setBand(band);
    if (band !== '' && channel !== '') {
      setFrequency(vtxTable[band].channels[Number(channel)-1])
      if (props?.onBandChannelChange) {
        props.onBandChannelChange(band+channel);
      }
    }
  };

  const selectChannel = (channel) => {
    setChannel(channel);
    if (band !== '' && channel !== '') {
      setFrequency(vtxTable[band].channels[Number(channel)-1])
      if (props?.onBandChannelChange) {
        props.onBandChannelChange(band+channel);
      }
    }
  };

  return (
    <div>
    <InputLabel id="band-label">Band</InputLabel>
    <Select labelId="band-label" value={band} defaultValue=""
    onChange={(evt) => selectBand(evt.target.value)}>
    {Object.entries(vtxTable).map((entry) => {
      const band = entry[0];
      return (
        <Tooltip key={band} value={band} title={entry[1].name}>
        <MenuItem>{band}</MenuItem>
        </Tooltip>
      );
    })}
    </Select>
    <InputLabel id="channel-label">Channel</InputLabel>
    <Select labelId="channel-label" value={channel} defaultValue=""
    onChange={(evt) => selectChannel(evt.target.value)}>
    {band in vtxTable && vtxTable[band].channels.map((freq, idx) => {
      const chan = idx + 1;
      return (
        <Tooltip key={chan} value={chan} title={freq}>
        <MenuItem>{chan}</MenuItem>
        </Tooltip>
      );
    })}
    </Select>
    <InputLabel id="frequency-label">Frequency</InputLabel>
    <Input labelId="frequency-label" value={frequency}
      onChange={(evt) => changeFrequency(evt.target.value)}
      inputProps={{
      step: 5,
      min: 5645,
      max: 5945,
      type: 'number'
    }}/>
    </div>
  );
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
    <InputLabel id="enter-label">Enter trigger value</InputLabel>
    <Input labelId="enter-label" value={enterTrigger}
      onChange={(evt) => changeEnterTrigger(evt.target.value)}
      inputProps={{
      step: 1,
      min: 0,
      max: 255,
      type: 'number'
    }}/>
    <InputLabel id="exit-label">Exit trigger value</InputLabel>
    <Input labelId="exit-label" value={exitTrigger}
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

function LapRFConfig(props) {
  return (
    <TimerConfig node={props.node} vtxTable={props.vtxTable} annTopic={props.annTopic} ctrlTopic={props.ctrlTopic}/>
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
  const [order, setOrder] = useState(props.order);
  const [seat, setSeat] = useState(props.seat);
  const [location, setLocation] = useState(props.location);

  const changeOrder = (v) => {
    setOrder(v);
  };

  const changeSeat = (s) => {
    setSeat(s);
  };

  const changeLocation = (loc) => {
    setLocation(loc);
  };

  return (
    <div>
    <FlagIcon/>
    <InputLabel id="order-label">Track order</InputLabel>
    <Input labelId="order-label" value={order}
      onChange={(evt) => changeOrder(evt.target.value)}
      inputProps={{
      step: 1,
      min: 1,
      type: 'number'
    }}/>
    <InputLabel id="location-label">Location</InputLabel>
    <Input labelId="location-label" value={location}
      onChange={(evt) => changeLocation(evt.target.value)}
    />
    <EventSeatIcon/>
    <InputLabel id="seat-label">Seat</InputLabel>
    <Input labelId="seat-label" value={seat}
      onChange={(evt) => changeSeat(evt.target.value)}
      inputProps={{
      step: 1,
      min: 1,
      type: 'number'
    }}/>
    </div>
  );
}

export default function Setup(props) {
  const [setupData, setSetupData] = useState({});
  const [mqttConfig, setMqttConfig] = useState({});
  const [vtxTable, setVtxTable] = useState({});

  useEffect(() => {
    const loader = createSetupDataLoader();
    readData(loader, setSetupData);
  }, []);

  useEffect(() => {
    loadMqttConfig(setMqttConfig);
  }, []);

  useEffect(() => {
    loadVtxTable(setVtxTable);
  }, []);

  let order = 0;
  return (
    <List>
    {
      Object.entries(setupData).map((timerEntry) => {
        const timerId = timerEntry[0];
        const timer = timerEntry[1];
        order++;
        let seat = 0;
        return (
          <ListItem key={timerId}>
          <ComputerIcon/>
          {timerId}
          <List>
          {
            Object.entries(timer).map((nmEntry) => {
              const nmAddr = nmEntry[0];
              const nm = nmEntry[1];
              const createTimerConfig = getTimerConfigFactory(nm.type);
              return (
                <ListItem key={nmAddr}>
                <DeveloperBoardIcon/>
                {nmAddr}
                <List>
                {
                  Object.entries(nm.nodes).map((nodeEntry) => {
                    const nodeId = nodeEntry[0];
                    const node = nodeEntry[1];
                    const annTopic = mqttConfig ? [mqttConfig.timerAnnTopic, timerId, nmAddr, nodeId].join('/') : null;
                    const ctrlTopic = mqttConfig ? [mqttConfig.timerCtrlTopic, timerId, nmAddr, nodeId].join('/') : null;
                    const timerConfig = createTimerConfig(node, vtxTable, annTopic, ctrlTopic);
                    seat++;
                    return (
                      <ListItem key={nodeId}>
                      {node.id}
                      {timerConfig}
                      <TrackConfig order={order} seat={seat}/>
                      </ListItem>
                    );
                  })
                }
                </List>
                </ListItem>
              );
            })
            
          }
          </List>
          </ListItem>
        );
      })
    }
    </List>
  );
}

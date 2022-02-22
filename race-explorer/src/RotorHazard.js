import React, { useState, useEffect } from 'react';
import TextField from '@mui/material/TextField';
import { debounce } from 'lodash';
import Frequency from './Frequency.js';
import * as util from './util.js';
import { getMqttClient, createRssiDataLoader } from './rh-client.js';
import Plot from 'react-plotly.js';


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

function RssiChart(props) {
  const {
    timer, address, index,
    enterTrigger: givenEnterTrigger, exitTrigger: givenExitTrigger,
    enterTriggerChangesHook, exitTriggerChangesHook
  } = props;

  const [rssiData, setRssiData] = useState();
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

  util.useInterval(() => {
    const loader = createRssiDataLoader(timer, address, index);
    loader.load(null, (data) => {
      if (data && (data?.rssi?.length || data?.lifetime?.length)) {
        let minX = Number.MAX_SAFE_INTEGER;
        let maxX = 0;
        const rssi_x = [];
        const rssi_y = [];
        for (const t_y of data?.rssi) {
          const {t: x, y} = t_y;
          minX = Math.min(x, minX);
          maxX = Math.max(x, maxX);
          rssi_x.push(new Date(x));
          rssi_y.push(y);
        }
        const lifetime_x = [];
        const peakLifetime_y = [];
        const nadirLifetime_y = [];
        for (const t_y of data?.lifetime) {
          const {t: x, y} = t_y;
          minX = Math.min(x, minX);
          maxX = Math.max(x, maxX);
          lifetime_x.push(new Date(x));
          if (y >= 0) {
            peakLifetime_y.push(y);
            nadirLifetime_y.push(null);
          } else {
            peakLifetime_y.push(null);
            nadirLifetime_y.push(-y);
          }
        }
        setRssiData({
          minX: new Date(minX), maxX: new Date(maxX),
          rssi: {x: rssi_x, y: rssi_y},
          peakLifetime: {x: lifetime_x, y: peakLifetime_y},
          nadirLifetime: {x: lifetime_x, y: nadirLifetime_y}
        });
      } else {
        setRssiData(null);
      }
    });
  }, 250);

  let plotData;
  if (rssiData) {
    plotData = [
      {type: 'scatter', name: 'Enter', yaxis: 'y2', mode: 'lines',
        line: {color: 'lightgreen', dash: 'dot'}, connectgaps: false,
        x: [rssiData?.minX, rssiData?.maxX], y: [enterTrigger, enterTrigger]},
      {type: 'scatter', name: 'Exit', yaxis: 'y2', mode: 'lines',
        line: {color: 'plum', dash: 'dot'}, connectgaps: false,
        x: [rssiData?.minX, rssiData?.maxX], y: [exitTrigger, exitTrigger]},
      {type: 'scatter', name: 'RSSI', mode: 'lines', line: {color: 'lightcyan'},
        x: rssiData?.rssi.x, y: rssiData?.rssi.y},
      {type: 'scatter', name: 'Peak lifetime', yaxis: 'y2', mode: 'lines+markers',
        line: {color: 'green'}, marker: {size: 2, color: 'green'},
        x: rssiData?.peakLifetime.x, y: rssiData?.peakLifetime.y},
      {type: 'scatter', name: 'Nadir lifetime', yaxis: 'y2', mode: 'lines+markers',
        line: {color: 'purple'}, marker: {size: 2, color: 'purple'},
        x: rssiData?.nadirLifetime.x, y: rssiData?.nadirLifetime.y}
    ];
  } else {
    plotData = [];
  }

  return (
    <Plot data={plotData}
    layout={{
      yaxis: {
        title: 'RSSI'
      },
      yaxis2: {
        title: 'Lifetime',
        overlaying: 'y',
        side: 'right'
      }
    }}
    />
  );
}

function RHNodeConfig(props) {
  const {node, annTopic, ctrlTopic, vtxTable} = props;

  const [enterTrigger, setEnterTrigger] = useState(node.enterTrigger);
  const [exitTrigger, setExitTrigger] = useState(node.exitTrigger);

  const freq = node.frequency;
  const bc = node?.bandChannel ?? null;

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
      getMqttClient().publish(freqCtrlTopic, bc ? freq+','+bc : freq);
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
  

  useEffect(() => {
    if (mqttEnterTriggerSubscriber) {
      return mqttEnterTriggerSubscriber((level) => {setEnterTrigger(level);});
    }
  }, [mqttEnterTriggerSubscriber]);

  useEffect(() => {
    if (mqttExitTriggerSubscriber) {
      return mqttExitTriggerSubscriber((level) => {setExitTrigger(level);});
    }
  }, [mqttExitTriggerSubscriber]);

  return (
    <div>
    <Frequency frequency={freq.toString()} bandChannel={bc}
      onChange={mqttFrequencyPublisher}
      frequencyChangesHook={mqttFrequencySubscriber}
      bandChannelChangesHook={mqttBandChannelSubscriber}
      vtxTable={vtxTable}
    />
    <RssiChart timer={node.timer} address={node.address} index={node.index}
      enterTrigger={enterTrigger}
      exitTrigger={exitTrigger}
    />
    <EnterExitTriggers
      enterTrigger={enterTrigger.toString()}
      exitTrigger={exitTrigger.toString()}
      onEnterTriggerChange={mqttEnterTriggerPublisher}
      onExitTriggerChange={mqttExitTriggerPublisher}
    />
    </div>
  );
}

export default function RHNodeConfigFactory(node, vtxTable, annTopic, ctrlTopic) {
  return <RHNodeConfig node={node} vtxTable={vtxTable} annTopic={annTopic} ctrlTopic={ctrlTopic}/>;
};

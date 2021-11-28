import React, { useState, useEffect } from 'react';
import TextField from '@mui/material/TextField';
import { debounce } from 'lodash';
import Frequency from './Frequency.js';
import { getMqttClient } from './rh-client.js';


function ThresholdGain(props) {
  const [threshold, setThreshold] = useState(props.threshold);
  const [gain, setGain] = useState(props.gain);

  const thresholdChangesHook = props?.thresholdChangesHook;
  useEffect(() => {
    if (thresholdChangesHook) {
      return thresholdChangesHook((level) => {setThreshold(level);});
    }
  }, [thresholdChangesHook]);

  const gainChangesHook = props?.gainChangesHook;
  useEffect(() => {
    if (gainChangesHook) {
      return gainChangesHook((level) => {setGain(level);});
    }
  }, [gainChangesHook]);

  const changeThreshold = (level) => {
    setThreshold(level);
    if (props?.onThresholdChange) {
      props.onThresholdChange(level);
    }
  };

  const changeGain = (level) => {
    setGain(level);
    if (props?.onGainChange) {
      props.onGainChange(level);
    }
  };

  return (
    <div>
    <TextField label="Threshold" value={threshold}
      onChange={(evt) => changeThreshold(evt.target.value)}
      inputProps={{
      step: 1,
      min: 0,
      max: 3000,
      type: 'number'
    }}/>
    <TextField label="Gain" value={gain}
      onChange={(evt) => changeGain(evt.target.value)}
      inputProps={{
      step: 1,
      min: 0,
      max: 63,
      type: 'number'
    }}/>
    </div>
  );
}

export default function LapRFConfig(props) {
  const node = props.node;
  const freq = node.frequency;
  const bc = node?.bandChannel ?? null;
  const threshold = node.threshold;
  const gain = node.gain;
  
  let mqttFrequencyPublisher = null;
  let mqttFrequencySubscriber = null;
  let mqttBandChannelPublisher = null;
  let mqttBandChannelSubscriber = null;
  let mqttThresholdPublisher = null;
  let mqttThresholdSubscriber = null;
  let mqttGainPublisher = null;
  let mqttGainSubscriber = null;
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

    const thresholdAnnTopic = [props.annTopic, "threshold"].join('/');
    const thresholdCtrlTopic = [props.ctrlTopic, "threshold"].join('/');
    mqttThresholdPublisher = (level) => {getMqttClient().publish(thresholdCtrlTopic, level);};
    mqttThresholdSubscriber = (setThreshold) => {
      const mqttClient = getMqttClient();
      mqttClient.subscribeTo(thresholdAnnTopic, (payload) => {
        const newLevel = new TextDecoder('UTF-8').decode(payload);
        setThreshold(newLevel);
      });
      return () => {
        mqttClient.unsubscribeFrom(thresholdAnnTopic);
      };
    };

    const gainAnnTopic = [props.annTopic, "gain"].join('/');
    const gainCtrlTopic = [props.ctrlTopic, "gain"].join('/');
    mqttGainPublisher = (level) => {getMqttClient().publish(gainCtrlTopic, level);};
    mqttGainSubscriber = (setGain) => {
      const mqttClient = getMqttClient();
      mqttClient.subscribeTo(gainAnnTopic, (payload) => {
        const newLevel = new TextDecoder('UTF-8').decode(payload);
        setGain(newLevel);
      });
      return () => {
        mqttClient.unsubscribeFrom(gainAnnTopic);
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
    <ThresholdGain threshold={threshold.toString()} gain={gain.toString()}
      onThresholdChange={mqttThresholdPublisher}
      thresholdChangesHook={mqttThresholdSubscriber}
      onGainChange={mqttGainPublisher}
      gainChangesHook={mqttGainSubscriber}
    />
    </div>
  );
}

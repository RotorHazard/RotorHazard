import mqtt from 'mqtt';
import axios from 'axios';
import * as config from './rh-config.js';

export function createResultDataLoader() {
  return (processResults, raceEvents) => loadResultData(config.resultDataEndpoint, processResults, raceEvents);
}

async function loadResultData(endpoint, processResults, raceEvents) {
  const body = (await axios.get(endpoint)).data;
  processResults(body, raceEvents);
}

export function createSetupDataLoader() {
  return (processSetup, setupData) => loadSetupData(config.setupDataEndpoint, processSetup, setupData);
}

async function loadSetupData(endpoint, processSetup, setupData) {
  const body = (await axios.get(endpoint)).data;
  processSetup(body, setupData);
}

const vtxTable = {};

export async function loadVtxTable(setVtxTable) {
  if (Object.keys(vtxTable).length === 0) {
    const body = (await axios.get(config.vtxTableEndpoint)).data;
    for (let band of body.vtx_table.bands_list) {
      vtxTable[band.letter] = {
        name: band.name,
        channels: band.frequencies.filter((f) => f > 0)
      };
    }
  }
  setVtxTable(vtxTable);
}

export async function loadEventData(setEventData) {
  const body = (await axios.get(config.eventDataEndpoint)).data;
  setEventData(body);
}

export async function loadTrackData(setTrackData) {
  const body = (await axios.get(config.trackDataEndpoint)).data;
  setTrackData(body);
}

export async function storeTrackData(trackData) {
  try {
    await axios.post(config.trackDataEndpoint, trackData);
  } catch (ex) {
    console.log(ex);
  }
}

let mqttConfig = null;

export async function loadMqttConfig(setMqttConfig) {
  if (mqttConfig === null) {
    mqttConfig = (await axios.get(config.mqttConfigEndpoint)).data;
  }
  setMqttConfig(mqttConfig);
}

mqtt.MqttClient.prototype.topicHandlers = {};
function mqttTopicListener(topic, payload) {
  if (topic in this.topicHandlers) {
    const handler = this.topicHandlers[topic];
    handler(payload);
  }
};
mqtt.MqttClient.prototype.subscribeTo = function(topic, handler) {
  this.topicHandlers[topic] = handler;
  this.subscribe(topic);
};
mqtt.MqttClient.prototype.unsubscribeFrom = function(topic) {
  this.unsubscribe(topic);
  delete this.topicHandlers[topic];
};

let mqttClient = null;

export function getMqttClient() {
  if (mqttClient === null) {
    let mqttBroker = config.mqttBroker;
    if (mqttBroker === '') {
      mqttBroker = 'ws://'+window.location.hostname+':8083';
    }
    mqttClient = mqtt.connect(mqttBroker, config.mqttOptions);
    mqttClient.on('message', mqttTopicListener);
  }
  return mqttClient;
}

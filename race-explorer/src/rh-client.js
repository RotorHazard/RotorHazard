import mqtt from 'mqtt';
import * as config from './rh-config.js';

export function createResultDataLoader() {
  return (processResults, raceEvents) => loadResultData(config.resultDataEndpoint, processResults, raceEvents);
}

async function loadResultData(endpoint, processResults, raceEvents) {
  const body = await (await fetch(endpoint)).text();
  processResults(body, raceEvents);
}

export function createSetupDataLoader() {
  return (processSetup, setupData) => loadSetupData(config.setupDataEndpoint, processSetup, setupData);
}

async function loadSetupData(endpoint, processSetup, setupData) {
  const body = await (await fetch(endpoint)).text();
  processSetup(body, setupData);
}

const vtxTable = {};

export async function loadVtxTable(setVtxTable) {
  if (Object.keys(vtxTable).length === 0) {
    const body = await (await fetch(config.vtxTableEndpoint)).json();
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
  const body = await (await fetch(config.eventDataEndpoint)).json();
  setEventData(body);
}


let mqttConfig = null;

export async function loadMqttConfig(setMqttConfig) {
  if (mqttConfig === null) {
    mqttConfig = await (await fetch(config.mqttConfigEndpoint)).json();
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
    mqttClient = mqtt.connect(config.mqttBroker, config.mqttOptions);
    mqttClient.on('message', mqttTopicListener);
  }
  return mqttClient;
}

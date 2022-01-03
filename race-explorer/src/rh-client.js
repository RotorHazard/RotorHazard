import mqtt from 'mqtt';
import axios from 'axios';
import { createBaseLoader } from './util.js';
import * as config from './rh-config.js';

function createLoader(endpoint, opts={}) {
  const loader = createBaseLoader();
  loader.endpoint = endpoint;
  loader._load = async function(processor) {
    const body = (await axios.get(this.endpoint, {...opts, signal: this.aborter.signal})).data;
    let data;
    if (processor !== null) {
      data = {};
      processor(body, data);
    } else {
      data = body;
    }
    return data;
  };

  return loader;
}

export function createResultDataLoader() {
  return createLoader(config.resultDataEndpoint, {responseType: 'text', headers: {'Accept': 'application/jsonl'}});
}

export function createSetupDataLoader() {
  return createLoader(config.setupDataEndpoint, {responseType: 'text', headers: {'Accept': 'application/jsonl'}});
}

let vtxTable = null;

export function createVtxTableLoader() {
  const vtxTableLoader = createLoader(config.vtxTableEndpoint);
  vtxTableLoader._getCached = () => vtxTable;
  vtxTableLoader._cache = (data) => {vtxTable = data;};
  return vtxTableLoader;
}

export function createEventDataLoader(raceEvent) {
  return createLoader(config.eventDataEndpoint);
}

export async function storeEventData(eventData) {
  try {
    await axios.put(config.eventDataEndpoint, eventData);
  } catch (ex) {
    console.log(ex);
  }
}

export function createTrackDataLoader() {
  return createLoader(config.trackDataEndpoint);
}

export async function storeTrackData(trackData) {
  try {
    await axios.put(config.trackDataEndpoint, trackData);
  } catch (ex) {
    console.log(ex);
  }
}

export function createTimerMappingLoader() {
  return createLoader(config.timerMappingEndpoint);
}

export async function storeTimerMapping(timerMapping) {
  try {
    await axios.put(config.timerMappingEndpoint, timerMapping);
  } catch (ex) {
    console.log(ex);
  }
}

export function createRaceClassLoader() {
  return createLoader(config.raceClassEndpoint);
}

export async function storeRaceClasses(raceClasses) {
  try {
    await axios.put(config.raceClassEndpoint, raceClasses);
  } catch (ex) {
    console.log(ex);
  }
}

export function createPilotDataLoader() {
  return createLoader(config.pilotDataEndpoint);
}

export async function storePilotData(pilotData) {
  try {
    await axios.put(config.pilotDataEndpoint, pilotData);
  } catch (ex) {
    console.log(ex);
  }
}

let mqttConfig = null;

export function createMqttConfigLoader() {
  const mqttConfigLoader = createLoader(config.mqttConfigEndpoint);
  mqttConfigLoader._getCached = () => mqttConfig;
  mqttConfigLoader._cache = (data) => {mqttConfig = data;};
  return mqttConfigLoader;
}

let mqttClient = null;

export function getMqttClient() {
  if (mqttClient === null) {
    let mqttBroker = config.mqttBroker;
    if (mqttBroker === '') {
      mqttBroker = 'ws://'+window.location.hostname+':8083';
    }
    mqttClient = mqtt.connect(mqttBroker, config.mqttOptions);

    mqttClient.topicHandlers = {};
    mqttClient.subscribeTo = function(topic, handler) {
      this.topicHandlers[topic] = handler;
      this.subscribe(topic);
    };
    mqttClient.unsubscribeFrom = function(topic) {
      this.unsubscribe(topic);
      delete this.topicHandlers[topic];
    };
    mqttClient.mqttTopicListener = function(topic, payload) {
      if (topic in this.topicHandlers) {
        const handler = this.topicHandlers[topic];
        handler(payload);
      }
    };

    mqttClient.on('message', mqttClient.mqttTopicListener);
  }
  return mqttClient;
}

export async function calculateMetrics(pilotResults, setMetrics) {
  const body = (await axios.post(config.raceMetricsEndpoint, pilotResults)).data;
  setMetrics(body);
}

export async function generateHeats(endpoint, params, setRaces) {
  const body = (await axios.post(endpoint, params)).data;
  setRaces(body);
}

export async function syncEvent(loadData) {
  const body = (await axios.post(config.syncEventEndpoint)).data;
  loadData(body);
}

export function createHeatGeneratorLoader(endpoint) {
  return createLoader(endpoint);
}

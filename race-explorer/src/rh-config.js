const dev = false;

export let eventDataEndpoint;
export let setupDataEndpoint;
export let vtxTableEndpoint;
export let mqttConfigEndpoint;

if (dev) {
  eventDataEndpoint = '/race-explorer/dev/eventData.jsonl';
  setupDataEndpoint = '/race-explorer/dev/setupData.jsonl';
  vtxTableEndpoint = '/race-explorer/dev/vtx_table.json';
  mqttConfigEndpoint = '/race-explorer/dev/mqttConfig.json';
} else {
  eventDataEndpoint = '/raceEvent';
  setupDataEndpoint = '/timerSetup';
  vtxTableEndpoint = '/vtxTable';
  mqttConfigEndpoint = '/mqttConfig';
}

export const mqttBroker = 'ws://localhost:8080';
export const mqttOptions = {
  username: 'race',
  password: 'fu56rg20'
};

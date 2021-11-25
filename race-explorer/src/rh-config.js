const dev = false;

export let resultDataEndpoint;
export let eventDataEndpoint;
export let setupDataEndpoint;
export let vtxTableEndpoint;
export let mqttConfigEndpoint;

if (dev) {
  resultDataEndpoint = '/race-explorer/dev/resultData.jsonl';
  eventDataEndpoint = '/race-explorer/dev/eventData.jsonl';
  setupDataEndpoint = '/race-explorer/dev/setupData.jsonl';
  vtxTableEndpoint = '/race-explorer/dev/vtx_table.json';
  mqttConfigEndpoint = '/race-explorer/dev/mqttConfig.json';
} else {
  resultDataEndpoint = '/raceResults';
  eventDataEndpoint = '/raceEvent';
  setupDataEndpoint = '/timerSetup';
  vtxTableEndpoint = '/vtxTable';
  mqttConfigEndpoint = '/mqttConfig';
}

export const mqttBroker = '';
export const mqttOptions = {
  username: 'race-admin',
  password: 'fu56rg20'
};

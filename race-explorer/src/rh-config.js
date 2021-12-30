export let resultDataEndpoint;
export let eventDataEndpoint;
export let setupDataEndpoint;
export let trackDataEndpoint;
export let timerMappingEndpoint;
export let raceClassEndpoint;
export let vtxTableEndpoint;
export let mqttConfigEndpoint;

if (process.env.NODE_ENV === 'development') {
  resultDataEndpoint = '/race-explorer/dev/resultData.jsonl';
  eventDataEndpoint = '/race-explorer/dev/eventData.json';
  setupDataEndpoint = '/race-explorer/dev/setupData.jsonl';
  trackDataEndpoint = '/race-explorer/dev/trackData.json';
  timerMappingEndpoint = '/race-explorer/dev/timerMapping.json';
  raceClassEndpoint = '/race-explorer/dev/raceClasses.json';
  vtxTableEndpoint = '/race-explorer/dev/vtx_table.json';
  mqttConfigEndpoint = '/race-explorer/dev/mqttConfig.json';
} else {
  resultDataEndpoint = '/raceResults';
  eventDataEndpoint = '/raceEvent';
  setupDataEndpoint = '/timerSetup';
  trackDataEndpoint = '/trackLayout';
  timerMappingEndpoint = '/timerMapping';
  raceClassEndpoint = '/raceClasses';
  vtxTableEndpoint = '/vtxTable';
  mqttConfigEndpoint = '/mqttConfig';
}

export const mqttBroker = '';
export const mqttOptions = {
  username: 'race-admin',
  password: 'fu56rg20'
};

const endpoint = '/raceEvent';

export default function createLoader() {
  return (processEvents, raceEvents) => loadEventData(endpoint, processEvents, raceEvents);
}

async function loadEventData(endpoint, processEvents, raceEvents) {
  const body = await (await fetch(endpoint)).text();
  processEvents(body, raceEvents);
}

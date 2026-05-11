import { SAFE_SMOKE_ENDPOINT_IDS, TODO_ENDPOINTS } from '../src/lib/endpoints';
import { RotorHazardClient } from '../src/lib/rhClient';

const url = process.env.RH_SOCKET_URL ?? 'http://localhost:5000';
const requiredLoadEvents = ['leaderboard', 'pilot_data', 'current_heat', 'race_status', 'frequency_data'];

function assert(condition: unknown, message: string): asserts condition {
  if (!condition) {
    throw new Error(message);
  }
}

function endpoint(id: string) {
  const found = TODO_ENDPOINTS.find((item) => item.id === id);
  assert(found, `Endpoint ${id} is missing`);
  return found;
}

const client = new RotorHazardClient({
  url,
  autoConnect: false,
  autoJoinCluster: true,
  consoleLogging: false,
  timeoutMs: 5000,
  onLog: (entry) => {
    if (entry.event === 'heartbeat' || entry.event === 'node_data') {
      return;
    }
    const prefix = `${entry.ts} ${entry.level.toUpperCase()} ${entry.direction}${entry.event ? ` ${entry.event}` : ''}`;
    console.log(`${prefix} ${entry.message}`);
    if (entry.data !== undefined && entry.level !== 'debug') {
      const rendered = JSON.stringify(entry.data);
      console.log(rendered.length > 900 ? `${rendered.slice(0, 900)}...` : rendered);
    }
  },
});

async function run() {
  console.log(`Smoke endpoint ids: ${SAFE_SMOKE_ENDPOINT_IDS.join(', ')}`);
  console.log(`Connecting to ${url}`);

  await client.callEndpoint(endpoint('connect'));

  const timeResult = await client.callEndpoint(endpoint('get_server_time'));
  assert(
    typeof (timeResult.ack as { server_time_s?: unknown } | undefined)?.server_time_s === 'number',
    'get_server_time did not return server_time_s ACK',
  );

  const loadResult = await client.callEndpoint(endpoint('load_data'), endpoint('load_data').defaultPayload, 6500);
  const receivedNames = new Set(client.getHistory().map((item) => item.event));
  const missingRequiredLoadEvents = requiredLoadEvents.filter((event) => !receivedNames.has(event));
  assert(
    missingRequiredLoadEvents.length === 0,
    `load_data did not produce required events: ${missingRequiredLoadEvents.join(', ')}`,
  );

  if (loadResult.wait?.missing.length) {
    console.log('Optional load_data events not observed in timeout:');
    console.log(loadResult.wait.missing.join(', '));
  }

  await client.callEndpoint(endpoint('get_race_scheduled'));
  assert(client.getHistory('race_scheduled').length > 0, 'get_race_scheduled did not produce race_scheduled');

  await client.callEndpoint(endpoint('current_race_marshal'));
  await client.callEndpoint(endpoint('get_pilotrace'));

  console.log('Smoke required reads passed.');
}

run()
  .catch((error: unknown) => {
    console.error('Smoke failed:', error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await client.callEndpoint(endpoint('disconnect')).catch(() => undefined);
  });

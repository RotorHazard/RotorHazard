#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { io } from 'socket.io-client';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

const RaceStatus = {
  READY: 0,
  RACING: 1,
  DONE: 2,
  STAGING: 3,
};

const liveEvents = new Set([
  'leaderboard',
  'current_laps',
  'race_status',
  'current_heat',
  'pilot_data',
  'heat_data',
  'race_list',
  'race_scheduled',
  'phonetic_data',
  'phonetic_leader',
  'phonetic_text',
  'phonetic_split_call',
  'callouts',
  'first_pass_registered',
  'race_saved',
  'stage_ready',
  'stop_timer',
]);

const config = {
  url: process.env.RH_SOCKET_URL ?? 'http://localhost:5000',
  statePath: process.env.SIM_STATE ?? path.join(__dirname, '.state.json'),
  prefix: process.env.SIM_PREFIX ?? 'DRONLY',
  className: process.env.SIM_CLASS_NAME ?? `${process.env.SIM_PREFIX ?? 'DRONLY'} Sim Class`,
  heatName: process.env.SIM_HEAT_NAME ?? `${process.env.SIM_PREFIX ?? 'DRONLY'} Sim Heat`,
  pilots: Number.parseInt(process.env.SIM_PILOTS ?? process.env.SIM_NODES ?? '4', 10),
  nodes: Number.parseInt(process.env.SIM_NODES ?? '4', 10),
  laps: Number.parseInt(process.env.SIM_LAPS ?? '4', 10),
  minLapSec: Number.parseFloat(process.env.SIM_MIN_LAP_SEC ?? '1'),
  formatId: Number.parseInt(process.env.SIM_FORMAT_ID ?? '1', 10),
  timeoutMs: Number.parseInt(process.env.SIM_TIMEOUT_MS ?? '18000', 10),
  settleMs: Number.parseInt(process.env.SIM_SETTLE_MS ?? '650', 10),
  firstPassGapMs: Number.parseInt(process.env.SIM_FIRST_PASS_GAP_MS ?? '1300', 10),
  lapGapMs: Number.parseInt(process.env.SIM_LAP_GAP_MS ?? '1250', 10),
  nodeStaggerMs: Number.parseInt(process.env.SIM_NODE_STAGGER_MS ?? '220', 10),
  saveRace: process.env.SIM_SAVE !== '0',
  forceDiscard: process.env.SIM_FORCE_DISCARD === '1',
};

let socket;
const eventCounts = new Map();

function log(message, data) {
  const prefix = `[rh-sim ${new Date().toISOString()}]`;
  if (data === undefined) {
    console.log(`${prefix} ${message}`);
  } else {
    console.log(`${prefix} ${message}`, JSON.stringify(data));
  }
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function readState() {
  try {
    return JSON.parse(fs.readFileSync(config.statePath, 'utf8'));
  } catch {
    return {};
  }
}

function saveState(nextState) {
  fs.writeFileSync(config.statePath, `${JSON.stringify(nextState, null, 2)}\n`, 'utf8');
}

function eventSummary(event, payload) {
  if (event === 'race_status' && payload) {
    return { race_status: payload.race_status, heat: payload.race_heat_id, next_round: payload.next_round };
  }
  if (event === 'current_laps' && payload?.current?.node_index) {
    return { nodes: payload.current.node_index.length };
  }
  if (event === 'leaderboard' && payload?.current?.leaderboard) {
    const primary = payload.current.leaderboard.meta?.primary_leaderboard;
    return { primary, rows: primary ? payload.current.leaderboard[primary]?.length ?? 0 : 0 };
  }
  if (event === 'pilot_data' && payload?.pilots) {
    return { pilots: payload.pilots.length };
  }
  if (event === 'heat_data' && payload?.heats) {
    return { heats: payload.heats.length };
  }
  if (event === 'current_heat' && payload) {
    return { current_heat: payload.current_heat, nodes: Object.keys(payload.heatNodes ?? {}).length };
  }
  if (event === 'race_saved' && payload) {
    return { race_id: payload.race_id, heat_id: payload.heat_id };
  }
  return payload;
}

function connect() {
  return new Promise((resolve, reject) => {
    socket = io(config.url, {
      autoConnect: false,
      transports: ['websocket', 'polling'],
    });

    const timeout = setTimeout(() => {
      cleanup();
      reject(new Error(`Timed out connecting to ${config.url}`));
    }, config.timeoutMs);

    const cleanup = () => {
      clearTimeout(timeout);
      socket.off('connect', onConnect);
      socket.off('connect_error', onConnectError);
    };

    const onConnect = () => {
      cleanup();
      log(`connected to ${config.url}`, { id: socket.id });
      socket.emit('join_cluster');
      resolve();
    };

    const onConnectError = (error) => {
      cleanup();
      reject(error);
    };

    socket.onAny((event, ...args) => {
      eventCounts.set(event, (eventCounts.get(event) ?? 0) + 1);
      if (liveEvents.has(event)) {
        log(`in ${event}`, eventSummary(event, args[0]));
      }
    });

    socket.once('connect', onConnect);
    socket.once('connect_error', onConnectError);
    socket.connect();
  });
}

function disconnect() {
  if (socket?.connected) {
    socket.disconnect();
  }
}

function emit(event, payload) {
  if (payload === undefined) {
    log(`out ${event}`);
    socket.emit(event);
  } else {
    log(`out ${event}`, payload);
    socket.emit(event, payload);
  }
}

function waitForEvent(event, predicate = () => true, timeoutMs = config.timeoutMs) {
  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      cleanup();
      reject(new Error(`Timed out waiting for ${event}`));
    }, timeoutMs);

    const cleanup = () => {
      clearTimeout(timeout);
      socket.off(event, handler);
    };

    const handler = (...args) => {
      if (!predicate(args[0], args)) {
        return;
      }
      cleanup();
      resolve(args[0]);
    };

    socket.on(event, handler);
  });
}

function waitForEvents(events, timeoutMs = config.timeoutMs) {
  const wanted = [...new Set(events)];
  const seen = new Map();

  return new Promise((resolve, reject) => {
    const timeout = setTimeout(() => {
      cleanup();
      const missing = wanted.filter((event) => !seen.has(event));
      reject(new Error(`Timed out waiting for events: ${missing.join(', ')}`));
    }, timeoutMs);

    const handlers = new Map(
      wanted.map((event) => [
        event,
        (payload) => {
          seen.set(event, payload);
          if (seen.size === wanted.length) {
            cleanup();
            resolve(Object.fromEntries(seen));
          }
        },
      ]),
    );

    const cleanup = () => {
      clearTimeout(timeout);
      for (const [event, handler] of handlers) {
        socket.off(event, handler);
      }
    };

    for (const [event, handler] of handlers) {
      socket.on(event, handler);
    }
  });
}

async function emitAndWait(event, payload, waitEvents, timeoutMs = config.timeoutMs) {
  const wait = waitEvents?.length ? waitForEvents(waitEvents, timeoutMs) : Promise.resolve({});
  emit(event, payload);
  return wait;
}

async function snapshot(loadTypes = ['pilot_data', 'heat_data', 'class_data', 'format_data', 'frequency_data', 'current_heat', 'race_status']) {
  const eventNames = [...new Set(loadTypes.map((loadType) => {
    if (loadType === 'frequency_data') return 'frequency_data';
    if (loadType === 'pilot_data') return 'pilot_data';
    if (loadType === 'heat_data') return 'heat_data';
    if (loadType === 'class_data') return 'class_data';
    if (loadType === 'format_data') return 'format_data';
    return loadType;
  }))];
  const wait = waitForEvents(eventNames);
  emit('load_data', { load_types: loadTypes });
  return wait;
}

async function ensureReadyOrDiscard(currentStatus) {
  if (currentStatus === RaceStatus.READY) {
    return;
  }
  if (!config.forceDiscard) {
    throw new Error(
      `Race status is ${currentStatus}, not READY. Stop/save/discard it first, or rerun with SIM_FORCE_DISCARD=1 for simulation cleanup.`,
    );
  }
  log('discarding existing active/finished laps because SIM_FORCE_DISCARD=1');
  await emitAndWait('discard_laps', undefined, ['race_status', 'current_laps', 'leaderboard']);
}

async function ensureRaceClass() {
  let snap = await snapshot(['class_data', 'format_data']);
  let classes = snap.class_data?.classes ?? [];
  let raceClass = classes
    .filter((item) => item.name === config.className || item.displayname === config.className)
    .sort((a, b) => b.id - a.id)[0];

  if (!raceClass) {
    const beforeIds = new Set(classes.map((item) => item.id));
    emit('add_race_class');
    await sleep(config.settleMs);
    snap = await snapshot(['class_data']);
    classes = snap.class_data?.classes ?? [];
    raceClass = classes.filter((item) => !beforeIds.has(item.id)).sort((a, b) => b.id - a.id)[0];
    if (!raceClass) {
      throw new Error('Could not create race class');
    }
  }

  if (raceClass.name !== config.className || Number(raceClass.format ?? 0) !== config.formatId) {
    emit('alter_race_class', {
      class_id: raceClass.id,
      class_name: config.className,
      class_format: config.formatId,
    });
    await sleep(config.settleMs);
    snap = await snapshot(['class_data']);
    raceClass = (snap.class_data?.classes ?? []).find((item) => item.id === raceClass.id) ?? raceClass;
  }

  log('race class ready', { id: raceClass.id, name: raceClass.displayname ?? raceClass.name, format: raceClass.format });
  return raceClass;
}

async function ensurePilots() {
  let snap = await snapshot(['pilot_data']);
  let pilots = snap.pilot_data?.pilots ?? [];
  const ready = [];
  const colors = ['#f04438', '#1570ef', '#12b76a', '#f79009', '#7a5af8', '#06aed4', '#d444f1', '#344054'];

  for (let index = 1; index <= config.pilots; index += 1) {
    const callsign = `${config.prefix}-${index}`;
    let pilot = pilots.find((item) => item.callsign === callsign);

    if (!pilot) {
      const beforeIds = new Set(pilots.map((item) => item.pilot_id));
      emit('add_pilot');
      await sleep(config.settleMs);
      snap = await snapshot(['pilot_data']);
      pilots = snap.pilot_data?.pilots ?? [];
      pilot = pilots.filter((item) => !beforeIds.has(item.pilot_id)).sort((a, b) => b.pilot_id - a.pilot_id)[0];
      if (!pilot) {
        throw new Error(`Could not create pilot ${callsign}`);
      }
    }

    emit('alter_pilot', {
      pilot_id: pilot.pilot_id,
      callsign,
      name: `${config.prefix} Pilot ${index}`,
      phonetic: `${config.prefix} ${index}`,
      team_name: index % 2 ? 'A' : 'B',
      color: colors[(index - 1) % colors.length],
    });
    await sleep(config.settleMs);
    snap = await snapshot(['pilot_data']);
    pilots = snap.pilot_data?.pilots ?? [];
    pilot = pilots.find((item) => item.callsign === callsign) ?? pilot;
    ready.push(pilot);
  }

  log('pilots ready', ready.map((pilot) => ({ id: pilot.pilot_id, callsign: pilot.callsign })));
  return ready;
}

async function ensureHeat(raceClass, pilots) {
  let snap = await snapshot(['heat_data', 'frequency_data']);
  const nodeCount = snap.frequency_data?.fdata?.length ?? 0;
  if (nodeCount < config.nodes) {
    throw new Error(
      `Server has ${nodeCount} node(s), but simulation needs ${config.nodes}. Start backend with ./simulate/00_start_mock_server.sh or RH_NODES=${config.nodes}.`,
    );
  }

  let heats = snap.heat_data?.heats ?? [];
  let heat = heats
    .filter((item) => (item.name === config.heatName || item.displayname === config.heatName) && (item.slots?.length ?? 0) >= config.nodes)
    .sort((a, b) => b.id - a.id)[0];

  if (!heat) {
    const beforeIds = new Set(heats.map((item) => item.id));
    emit('add_heat', { class: raceClass.id });
    await sleep(config.settleMs);
    snap = await snapshot(['heat_data']);
    heats = snap.heat_data?.heats ?? [];
    heat = heats.filter((item) => !beforeIds.has(item.id)).sort((a, b) => b.id - a.id)[0];
    if (!heat) {
      throw new Error('Could not create heat');
    }
  }

  emit('alter_heat', {
    heat: heat.id,
    name: config.heatName,
    class: raceClass.id,
    active: true,
    auto_frequency: false,
  });
  await sleep(config.settleMs);

  snap = await snapshot(['heat_data']);
  heat = (snap.heat_data?.heats ?? []).find((item) => item.id === heat.id) ?? heat;
  const slots = [...(heat.slots ?? [])]
    .filter((slot) => slot.node_index !== null && slot.node_index !== undefined)
    .sort((a, b) => a.node_index - b.node_index)
    .slice(0, config.nodes);

  if (slots.length < config.nodes) {
    throw new Error(`Heat ${heat.id} has ${slots.length} slot(s), expected ${config.nodes}`);
  }

  for (let index = 0; index < config.nodes; index += 1) {
    emit('alter_heat', {
      heat: heat.id,
      slot_id: slots[index].id,
      pilot: pilots[index % pilots.length].pilot_id,
      method: 0,
    });
    await sleep(180);
  }
  await sleep(config.settleMs);

  snap = await snapshot(['heat_data']);
  heat = (snap.heat_data?.heats ?? []).find((item) => item.id === heat.id) ?? heat;
  log('heat ready', { id: heat.id, name: heat.displayname ?? heat.name, slots: heat.slots?.length ?? 0 });
  return heat;
}

async function prepare() {
  let snap = await snapshot();
  await ensureReadyOrDiscard(snap.race_status?.race_status);
  const nodeCount = snap.frequency_data?.fdata?.length ?? 0;
  if (nodeCount < config.nodes) {
    throw new Error(
      `Server has ${nodeCount} node(s), but simulation needs ${config.nodes}. Start backend with ./simulate/00_start_mock_server.sh or RH_NODES=${config.nodes}.`,
    );
  }

  emit('set_min_lap', { min_lap: config.minLapSec });
  emit('set_min_first_crossing', { min_first_crossing: 0 });
  emit('set_min_lap_behavior', { min_lap_behavior: 0 });
  await sleep(config.settleMs);

  const raceClass = await ensureRaceClass();
  const pilots = await ensurePilots();
  const heat = await ensureHeat(raceClass, pilots);

  await emitAndWait('set_current_heat', { heat: heat.id }, ['current_heat', 'leaderboard', 'current_laps', 'race_status']);
  snap = await snapshot(['current_heat', 'race_status']);

  const state = {
    url: config.url,
    prefix: config.prefix,
    classId: raceClass.id,
    heatId: heat.id,
    nodeCount: config.nodes,
    pilotIds: pilots.map((pilot) => pilot.pilot_id),
    updatedAt: new Date().toISOString(),
    raceStatus: snap.race_status?.race_status,
  };
  saveState(state);
  log('simulation event setup ready', state);
  return state;
}

async function startRace() {
  const state = readState();
  if (!state.heatId) {
    throw new Error('No simulation state found. Run 01_prepare_event.sh first.');
  }

  let snap = await snapshot(['race_status', 'current_heat']);
  await ensureReadyOrDiscard(snap.race_status?.race_status);

  await emitAndWait('set_current_heat', { heat: state.heatId }, ['current_heat', 'leaderboard', 'current_laps', 'race_status']);
  emit('stage_race');
  await waitForEvent('race_status', (payload) => payload?.race_status === RaceStatus.RACING, config.timeoutMs + 8000);

  const nextState = { ...state, startedAt: new Date().toISOString(), raceStatus: RaceStatus.RACING };
  saveState(nextState);
  log('race is racing', { heatId: state.heatId });
  return nextState;
}

async function driveLaps() {
  const state = readState();
  const nodeCount = state.nodeCount ?? config.nodes;
  const snap = await snapshot(['race_status']);
  if (snap.race_status?.race_status !== RaceStatus.RACING) {
    throw new Error(`Race is not RACING. Current status: ${snap.race_status?.race_status}. Run 02_start_race.sh first.`);
  }

  log('sending first passes', { nodes: nodeCount });
  for (let node = 0; node < nodeCount; node += 1) {
    await emitAndWait('simulate_lap', { node }, ['current_laps', 'leaderboard']);
    await sleep(config.nodeStaggerMs);
  }

  await sleep(config.firstPassGapMs);

  for (let lap = 1; lap <= config.laps; lap += 1) {
    log(`sending lap ${lap}`, { nodes: nodeCount });
    const order = [...Array(nodeCount).keys()].sort((a, b) => ((a + lap) % nodeCount) - ((b + lap) % nodeCount));
    for (const node of order) {
      await emitAndWait('simulate_lap', { node }, ['current_laps', 'leaderboard']);
      await sleep(config.nodeStaggerMs);
    }
    await sleep(config.lapGapMs);
  }

  await sleep(config.settleMs);
  log('laps sent', Object.fromEntries([...eventCounts.entries()].filter(([event]) => liveEvents.has(event))));
}

async function stopAndSave() {
  const snap = await snapshot(['race_status']);
  const raceStatus = snap.race_status?.race_status;

  if (raceStatus === RaceStatus.RACING || raceStatus === RaceStatus.STAGING) {
    await emitAndWait('stop_race', undefined, ['race_status', 'leaderboard'], config.timeoutMs);
    await waitForEvent('race_status', (payload) => payload?.race_status === RaceStatus.DONE, 5000).catch(() => undefined);
  } else {
    log('race is not active; skipping stop', { raceStatus });
  }

  if (config.saveRace) {
    emit('save_laps');
    await Promise.race([
      waitForEvent('race_saved', () => true, config.timeoutMs),
      waitForEvent('race_status', (payload) => payload?.race_status === RaceStatus.READY, config.timeoutMs),
    ]).catch((error) => {
      log(`save wait warning: ${error.message}`);
    });
    await sleep(config.settleMs);
  }

  log('stop/save complete', Object.fromEntries([...eventCounts.entries()].filter(([event]) => liveEvents.has(event))));
}

function usage() {
  console.log(`Usage: node rh_sim_client.mjs <prepare|start|laps|stop|full>

Environment:
  RH_SOCKET_URL=${config.url}
  SIM_NODES=${config.nodes}
  SIM_PILOTS=${config.pilots}
  SIM_LAPS=${config.laps}
  SIM_PREFIX=${config.prefix}
  SIM_SAVE=${config.saveRace ? '1' : '0'}
`);
}

async function main() {
  const command = process.argv[2];
  if (!command || command === '--help' || command === '-h') {
    usage();
    return;
  }

  await connect();
  try {
    if (command === 'prepare') {
      await prepare();
    } else if (command === 'start') {
      await startRace();
    } else if (command === 'laps') {
      await driveLaps();
    } else if (command === 'stop') {
      await stopAndSave();
    } else if (command === 'full') {
      await prepare();
      await startRace();
      await driveLaps();
      await stopAndSave();
    } else {
      throw new Error(`Unknown command: ${command}`);
    }
  } finally {
    disconnect();
  }
}

main().catch((error) => {
  console.error(`[rh-sim] ${error.stack ?? error.message}`);
  disconnect();
  process.exitCode = 1;
});

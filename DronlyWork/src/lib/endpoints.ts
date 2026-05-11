import type {
  CalcPilotsRequest,
  CalcResetRequest,
  GetPilotRaceRequest,
  LoadDataRequest,
  ReplaceCurrentLapsRequest,
  ResaveLapsRequest,
  ScheduleRaceRequest,
  SetCurrentHeatRequest,
  SocketEventName,
  SocketServerEventName,
} from '../../types';

export type EndpointAction = 'connect' | 'disconnect' | 'emit';

export interface EndpointDefinition {
  id: string;
  todoName: string;
  label: string;
  action: EndpointAction;
  eventName?: SocketEventName;
  readOnly: boolean;
  expectsAck?: boolean;
  defaultPayload?: unknown;
  expectedEvents: string[];
  notes: string;
}

export interface LiveRaceEventDefinition {
  eventName: SocketServerEventName;
  label: string;
  notes: string;
}

export const LIVE_RACE_BOOTSTRAP_LOAD_TYPES = [
  'leaderboard',
  'current_laps',
  'race_status',
  'current_heat',
  'pilot_data',
  'heat_data',
  'race_list',
  'callouts',
] as const;

export const LIVE_RACE_EVENTS: LiveRaceEventDefinition[] = [
  {
    eventName: 'leaderboard',
    label: 'Standings',
    notes: 'Current and previous race leaderboard data.',
  },
  {
    eventName: 'current_laps',
    label: 'Lap timings',
    notes: 'Per-node lap list, lap times, splits, and finished flags.',
  },
  {
    eventName: 'race_status',
    label: 'Race state',
    notes: 'Race clock/state, active heat/class, staging, and next round.',
  },
  {
    eventName: 'current_heat',
    label: 'Current heat',
    notes: 'Active heat assignment and node/pilot display data.',
  },
  {
    eventName: 'pilot_data',
    label: 'Pilots',
    notes: 'Pilot callsigns, names, colors, teams, phonetics, and attributes.',
  },
  {
    eventName: 'heat_data',
    label: 'Heats',
    notes: 'Heat definitions, slots, automation status, and attributes.',
  },
  {
    eventName: 'race_list',
    label: 'Race history',
    notes: 'Saved races grouped by heat and round.',
  },
  {
    eventName: 'race_scheduled',
    label: 'Scheduled start',
    notes: 'Pending scheduled race countdown state.',
  },
  {
    eventName: 'phonetic_data',
    label: 'Lap callout',
    notes: 'Pilot lap announcement payloads emitted during a race.',
  },
  {
    eventName: 'phonetic_leader',
    label: 'Leader callout',
    notes: 'Leader announcement payloads emitted during a race.',
  },
  {
    eventName: 'phonetic_text',
    label: 'Text callout',
    notes: 'Free-form announcement text from callouts/race state.',
  },
  {
    eventName: 'phonetic_split_call',
    label: 'Split callout',
    notes: 'Split timing and speed announcement payloads.',
  },
  {
    eventName: 'callouts',
    label: 'Callout config',
    notes: 'Saved voice callout snippets loaded by the race UI.',
  },
  {
    eventName: 'first_pass_registered',
    label: 'First pass',
    notes: 'First crossing notification for a node.',
  },
];

export const BASELINE_LOAD_TYPES = [
  'node_data',
  'environmental_data',
  'frequency_data',
  'heat_list',
  'heat_data',
  'seat_data',
  'class_list',
  'class_data',
  'format_data',
  'pilot_list',
  'pilot_data',
  'result_data',
  'node_tuning',
  'enter_and_exit_at_levels',
  'start_thresh_lower_amount',
  'start_thresh_lower_duration',
  'min_lap',
  'action_setup',
  'event_actions',
  'leaderboard',
  'current_laps',
  'race_status',
  'current_heat',
  'race_list',
  'language',
  'all_languages',
  'callouts',
  'imdtabler_page',
  'vrx_list',
  'exporter_list',
  'importer_list',
  'heatgenerator_list',
  'raceclass_rank_method_list',
  'race_points_method_list',
  'plugin_list',
  'plugin_repo',
  'cluster_status',
] as const;

export const BASELINE_LOAD_EVENTS = [
  'node_data',
  'environmental_data',
  'frequency_data',
  'heat_list',
  'heat_data',
  'seat_data',
  'class_list',
  'class_data',
  'format_data',
  'pilot_data',
  'result_data',
  'node_tuning',
  'enter_and_exit_at_levels',
  'start_thresh_lower_amount',
  'start_thresh_lower_duration',
  'min_lap',
  'action_setup',
  'event_actions',
  'leaderboard',
  'current_laps',
  'race_status',
  'current_heat',
  'race_list',
  'language',
  'all_languages',
  'imdtabler_data',
  'vrx_list',
  'exporter_list',
  'importer_list',
  'heatgenerator_list',
  'raceclass_rank_method_list',
  'race_points_method_list',
  'plugin_list',
  'plugin_repo',
] as const;

const defaultLoadDataPayload: LoadDataRequest = {
  load_types: [...BASELINE_LOAD_TYPES],
};

const defaultHeatPayload = { heat: 1 };
const defaultSetCurrentHeatPayload: SetCurrentHeatRequest = { heat: null };
const defaultScheduleRacePayload: ScheduleRaceRequest = { m: 0, s: 10 };
const defaultCalcPilotsPayload: CalcPilotsRequest = { heat: 1, preassignments: {} };
const defaultCalcResetPayload: CalcResetRequest = { heat: 1 };
const defaultGetPilotRacePayload: GetPilotRaceRequest = { pilotrace_id: 1 };

const defaultResavePayload: ResaveLapsRequest = {
  heat_id: 1,
  round_id: 1,
  callsign: 'Example',
  race_id: 1,
  pilotrace_id: 1,
  seat: 0,
  pilot_id: 1,
  enter_at: 90,
  exit_at: 80,
  laps: [
    {
      lap_time_stamp: 0,
      lap_time: 0,
      source: 0,
      deleted: false,
      peak_rssi: null,
    },
  ],
};

const defaultReplacePayload: ReplaceCurrentLapsRequest = {
  ...defaultResavePayload,
};

export const TODO_ENDPOINTS: EndpointDefinition[] = [
  {
    id: 'connect',
    todoName: 'connect',
    label: 'Connect socket',
    action: 'connect',
    readOnly: true,
    expectedEvents: ['connect'],
    notes: 'Socket.IO lifecycle event. The client also emits join_cluster after connect.',
  },
  {
    id: 'disconnect',
    todoName: 'disconnect',
    label: 'Disconnect socket',
    action: 'disconnect',
    readOnly: true,
    expectedEvents: ['disconnect'],
    notes: 'Socket.IO lifecycle event.',
  },
  {
    id: 'load_data',
    todoName: 'load_data',
    label: 'Load baseline data',
    action: 'emit',
    eventName: 'load_data',
    readOnly: true,
    defaultPayload: defaultLoadDataPayload,
    expectedEvents: [...BASELINE_LOAD_EVENTS],
    notes: 'Requests many RotorHazard read models in one call.',
  },
  {
    id: 'set_current_heat',
    todoName: 'set_current_heat',
    label: 'Set current heat',
    action: 'emit',
    eventName: 'set_current_heat',
    readOnly: false,
    defaultPayload: defaultSetCurrentHeatPayload,
    expectedEvents: ['race_status'],
    notes: 'Mutates the active heat. Default payload switches to practice mode with heat=null.',
  },
  {
    id: 'activate_heat',
    todoName: 'activate_heat',
    label: 'Activate heat',
    action: 'emit',
    eventName: 'activate_heat',
    readOnly: false,
    defaultPayload: defaultHeatPayload,
    expectedEvents: ['heat_data'],
    notes: 'Mutates heat active state.',
  },
  {
    id: 'deactivate_heat',
    todoName: 'deactivate_heat',
    label: 'Deactivate heat',
    action: 'emit',
    eventName: 'deactivate_heat',
    readOnly: false,
    defaultPayload: defaultHeatPayload,
    expectedEvents: ['heat_data'],
    notes: 'Mutates heat active state.',
  },
  {
    id: 'alter_race',
    todoName: 'alter_race',
    label: 'Alter saved race heat',
    action: 'emit',
    eventName: 'alter_race',
    readOnly: false,
    defaultPayload: { race_id: 1, heat_id: 1 },
    expectedEvents: ['heat_data', 'race_list', 'result_data', 'priority_message'],
    notes: 'Retroactively reassigns a saved race to a heat.',
  },
  {
    id: 'current_race_marshal',
    todoName: 'current_race_marshal',
    label: 'Read current race marshal',
    action: 'emit',
    eventName: 'current_race_marshal',
    readOnly: true,
    defaultPayload: null,
    expectedEvents: ['current_marshal_data'],
    notes: 'Only emits data when the current race is DONE and not practice.',
  },
  {
    id: 'get_server_time',
    todoName: 'get_server_time',
    label: 'Get server time',
    action: 'emit',
    eventName: 'get_server_time',
    readOnly: true,
    expectsAck: true,
    defaultPayload: null,
    expectedEvents: [],
    notes: 'Returns Socket.IO ACK with server_time_s. This is Python monotonic() seconds, not wall-clock date/time.',
  },
  {
    id: 'schedule_race',
    todoName: 'schedule_race',
    label: 'Schedule race',
    action: 'emit',
    eventName: 'schedule_race',
    readOnly: false,
    defaultPayload: defaultScheduleRacePayload,
    expectedEvents: ['race_scheduled', 'race_status'],
    notes: 'Schedules a race countdown.',
  },
  {
    id: 'cancel_schedule_race',
    todoName: 'cancel_schedule_race',
    label: 'Cancel scheduled race',
    action: 'emit',
    eventName: 'cancel_schedule_race',
    readOnly: false,
    defaultPayload: null,
    expectedEvents: ['race_scheduled', 'race_status'],
    notes: 'Cancels pending scheduled start.',
  },
  {
    id: 'stage_race',
    todoName: 'stage_race',
    label: 'Stage race',
    action: 'emit',
    eventName: 'stage_race',
    readOnly: false,
    defaultPayload: null,
    expectedEvents: ['race_status', 'stage_timer'],
    notes: 'Moves race toward staging/start state.',
  },
  {
    id: 'stop_race',
    todoName: 'stop_race',
    label: 'Stop race',
    action: 'emit',
    eventName: 'stop_race',
    readOnly: false,
    defaultPayload: null,
    expectedEvents: ['race_status', 'leaderboard', 'current_laps'],
    notes: 'Stops current race.',
  },
  {
    id: 'save_laps',
    todoName: 'save_laps',
    label: 'Save laps',
    action: 'emit',
    eventName: 'save_laps',
    readOnly: false,
    defaultPayload: null,
    expectedEvents: ['leaderboard', 'current_laps', 'race_list', 'result_data'],
    notes: 'Persists current race laps if there is a race to save.',
  },
  {
    id: 'resave_laps',
    todoName: 'resave_laps',
    label: 'Resave saved laps',
    action: 'emit',
    eventName: 'resave_laps',
    readOnly: false,
    defaultPayload: defaultResavePayload,
    expectedEvents: ['priority_message', 'leaderboard', 'current_laps', 'result_data'],
    notes: 'Requires real saved race ids. The default payload is only a shape template.',
  },
  {
    id: 'replace_current_laps',
    todoName: 'replace_current_laps',
    label: 'Replace current laps',
    action: 'emit',
    eventName: 'replace_current_laps',
    readOnly: false,
    defaultPayload: defaultReplacePayload,
    expectedEvents: ['current_laps', 'leaderboard', 'race_status'],
    notes: 'Requires valid current race data. The default payload is only a shape template.',
  },
  {
    id: 'discard_laps',
    todoName: 'discard_laps',
    label: 'Discard current laps',
    action: 'emit',
    eventName: 'discard_laps',
    readOnly: false,
    defaultPayload: null,
    expectedEvents: ['current_laps', 'leaderboard', 'race_status'],
    notes: 'Discards unsaved current race laps.',
  },
  {
    id: 'calc_pilots',
    todoName: 'calc_pilots',
    label: 'Calculate heat pilots',
    action: 'emit',
    eventName: 'calc_pilots',
    readOnly: false,
    defaultPayload: defaultCalcPilotsPayload,
    expectedEvents: ['heat_data'],
    notes: 'Runs heat automation for one heat.',
  },
  {
    id: 'calc_reset',
    todoName: 'calc_reset',
    label: 'Reset heat calculation',
    action: 'emit',
    eventName: 'calc_reset',
    readOnly: false,
    defaultPayload: defaultCalcResetPayload,
    expectedEvents: ['heat_data'],
    notes: 'Resets heat planning status.',
  },
  {
    id: 'get_race_scheduled',
    todoName: 'get_race_scheduled',
    label: 'Read scheduled race',
    action: 'emit',
    eventName: 'get_race_scheduled',
    readOnly: true,
    defaultPayload: null,
    expectedEvents: ['race_scheduled'],
    notes: 'Reads race scheduled flag and scheduled time.',
  },
  {
    id: 'get_pilotrace',
    todoName: 'get_pilotrace',
    label: 'Read pilot race details',
    action: 'emit',
    eventName: 'get_pilotrace',
    readOnly: true,
    defaultPayload: defaultGetPilotRacePayload,
    expectedEvents: ['race_details'],
    notes: 'Requires an existing saved pilotrace_id.',
  },
];

export const SAFE_SMOKE_ENDPOINT_IDS = [
  'connect',
  'load_data',
  'get_server_time',
  'get_race_scheduled',
  'current_race_marshal',
  'get_pilotrace',
  'disconnect',
] as const;

export const DEFAULT_MARKED_ENDPOINT_IDS = [
  'load_data',
  'get_server_time',
  'get_race_scheduled',
] as const;

import { useEffect, useMemo, useRef, useState } from 'react';
import type { CSSProperties, FormEvent } from 'react';
import { BASELINE_LOAD_EVENTS, BASELINE_LOAD_TYPES } from './lib/endpoints';
import { formatJson, RotorHazardClient, type ReceivedEvent } from './lib/rhClient';

const DEFAULT_URL = import.meta.env.VITE_RH_SOCKET_URL || 'http://localhost:5000';

type Dict = Record<string, unknown>;

interface DatasetEntry {
  event: string;
  payload: unknown;
  updatedAt: string;
  count: number;
}

interface DatasetMeta {
  event: string;
  label: string;
  group: string;
}

interface ClockSample {
  localAt: number;
  serverTimeS: number;
}

interface Announcement {
  id: number;
  event: string;
  message: string;
  at: string;
}

const DATASET_CATALOG: DatasetMeta[] = [
  { event: 'race_status', label: 'Race Status', group: 'Race' },
  { event: 'leaderboard', label: 'Leaderboard', group: 'Race' },
  { event: 'current_laps', label: 'Current Laps', group: 'Race' },
  { event: 'current_heat', label: 'Current Heat', group: 'Race' },
  { event: 'race_list', label: 'Race History', group: 'Race' },
  { event: 'result_data', label: 'Results', group: 'Race' },
  { event: 'pilot_data', label: 'Pilots', group: 'Event Setup' },
  { event: 'heat_data', label: 'Heats', group: 'Event Setup' },
  { event: 'heat_list', label: 'Heat List', group: 'Event Setup' },
  { event: 'class_data', label: 'Classes', group: 'Event Setup' },
  { event: 'class_list', label: 'Class List', group: 'Event Setup' },
  { event: 'format_data', label: 'Formats', group: 'Event Setup' },
  { event: 'seat_data', label: 'Seats', group: 'Timing' },
  { event: 'node_data', label: 'Nodes', group: 'Timing' },
  { event: 'frequency_data', label: 'Frequencies', group: 'Timing' },
  { event: 'environmental_data', label: 'Environment', group: 'Timing' },
  { event: 'node_tuning', label: 'Profile', group: 'Timing' },
  { event: 'enter_and_exit_at_levels', label: 'Thresholds', group: 'Timing' },
  { event: 'start_thresh_lower_amount', label: 'Start Threshold Amount', group: 'Timing' },
  { event: 'start_thresh_lower_duration', label: 'Start Threshold Duration', group: 'Timing' },
  { event: 'min_lap', label: 'Lap Rules', group: 'Timing' },
  { event: 'action_setup', label: 'Action Setup', group: 'System' },
  { event: 'event_actions', label: 'Event Actions', group: 'System' },
  { event: 'language', label: 'Language', group: 'System' },
  { event: 'all_languages', label: 'Language Dictionary', group: 'System' },
  { event: 'callouts', label: 'Callouts', group: 'System' },
  { event: 'imdtabler_data', label: 'IMDTabler', group: 'System' },
  { event: 'vrx_list', label: 'Video Receivers', group: 'System' },
  { event: 'exporter_list', label: 'Exporters', group: 'System' },
  { event: 'importer_list', label: 'Importers', group: 'System' },
  { event: 'heatgenerator_list', label: 'Heat Generators', group: 'System' },
  { event: 'raceclass_rank_method_list', label: 'Class Ranking', group: 'System' },
  { event: 'race_points_method_list', label: 'Points Methods', group: 'System' },
  { event: 'plugin_list', label: 'Plugins', group: 'System' },
  { event: 'plugin_repo', label: 'Plugin Repository', group: 'System' },
  { event: 'cluster_status', label: 'Cluster', group: 'System' },
];

const DATASET_EVENTS = [...new Set([...BASELINE_LOAD_EVENTS, ...DATASET_CATALOG.map((item) => item.event)])];

const LIVE_ANNOUNCEMENT_EVENTS = new Set([
  'phonetic_data',
  'phonetic_leader',
  'phonetic_text',
  'phonetic_split_call',
  'first_pass_registered',
  'race_saved',
]);

const RACE_STATUS = {
  READY: 0,
  RACING: 1,
  DONE: 2,
  STAGING: 3,
} as const;

function isRecord(value: unknown): value is Dict {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function toRecord(value: unknown): Dict {
  return isRecord(value) ? value : {};
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function asRecordArray(value: unknown): Dict[] {
  return asArray(value).filter(isRecord);
}

function asString(value: unknown, fallback = ''): string {
  if (value === null || value === undefined) {
    return fallback;
  }
  if (typeof value === 'string') {
    return value;
  }
  if (typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return fallback;
}

function asNumber(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === 'string' && value.trim() !== '') {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

function displayValue(value: unknown, fallback: unknown = '-'): string {
  const text = asString(value, '');
  return text.trim() ? text : asString(fallback, '-');
}

function truthyLabel(value: unknown): string {
  if (value === true || value === 1 || value === '1') {
    return 'yes';
  }
  if (value === false || value === 0 || value === '0') {
    return 'no';
  }
  return displayValue(value);
}

function formatDuration(totalSeconds: number | null, showSign = false): string {
  if (totalSeconds === null || !Number.isFinite(totalSeconds)) {
    return '--:--';
  }

  const sign = totalSeconds < 0 ? '-' : showSign ? '+' : '';
  const abs = Math.max(0, Math.abs(totalSeconds));
  const hours = Math.floor(abs / 3600);
  const minutes = Math.floor((abs % 3600) / 60);
  const seconds = Math.floor(abs % 60);
  const tenths = Math.floor((abs * 10) % 10);

  if (hours > 0) {
    return `${sign}${hours}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
  }

  return `${sign}${minutes}:${String(seconds).padStart(2, '0')}.${tenths}`;
}

function eventPayload(event: ReceivedEvent): unknown {
  return event.args.length === 1 ? event.args[0] : event.args;
}

function dataset(datasets: Record<string, DatasetEntry>, event: string): unknown {
  return datasets[event]?.payload;
}

function recordDataset(datasets: Record<string, DatasetEntry>, event: string): Dict {
  return toRecord(dataset(datasets, event));
}

function rowsFromPayload(payload: unknown, key: string): Dict[] {
  return asRecordArray(toRecord(payload)[key]);
}

function objectValuesAsRecords(value: unknown): Dict[] {
  if (!isRecord(value)) {
    return [];
  }

  return Object.values(value).filter(isRecord);
}

function findById(items: Dict[], id: unknown, keys: string[]): Dict | undefined {
  const target = asNumber(id);
  if (target === null) {
    return undefined;
  }

  return items.find((item) => keys.some((key) => asNumber(item[key]) === target));
}

function summarizeAnnouncement(event: string, payload: unknown): string {
  const data = toRecord(payload);
  if (event === 'phonetic_text') {
    return displayValue(data.text, 'Callout');
  }
  if (event === 'phonetic_leader') {
    return `${displayValue(data.callsign, displayValue(data.pilot, 'Pilot'))} leading`;
  }
  if (event === 'phonetic_data') {
    return `${displayValue(data.callsign, displayValue(data.pilot, 'Pilot'))} lap ${displayValue(data.lap)}`;
  }
  if (event === 'phonetic_split_call') {
    return `${displayValue(data.pilot_name, 'Pilot')} split ${displayValue(data.split_id)} ${displayValue(data.split_time)}`;
  }
  if (event === 'first_pass_registered') {
    return `Node ${Number(data.node_index ?? 0) + 1} first pass`;
  }
  if (event === 'race_saved') {
    return `Race saved #${displayValue(data.race_id)}`;
  }
  return event;
}

function raceStatusLabel(status: unknown): string {
  switch (asNumber(status)) {
    case RACE_STATUS.RACING:
      return 'Racing';
    case RACE_STATUS.DONE:
      return 'Done';
    case RACE_STATUS.STAGING:
      return 'Staging';
    case RACE_STATUS.READY:
      return 'Ready';
    default:
      return 'Unknown';
  }
}

function statusClass(status: unknown): string {
  switch (asNumber(status)) {
    case RACE_STATUS.RACING:
      return 'racing';
    case RACE_STATUS.DONE:
      return 'done';
    case RACE_STATUS.STAGING:
      return 'staging';
    default:
      return 'ready';
  }
}

function latestLap(laps: Dict[]): Dict | undefined {
  return [...laps].reverse().find((lap) => lap.deleted !== true);
}

function getLeaderboard(payload: unknown) {
  const root = toRecord(payload);
  const race = toRecord(root.current);
  const leaderboard = toRecord(race.leaderboard);
  const meta = toRecord(leaderboard.meta);
  const primary =
    asString(meta.primary_leaderboard) ||
    ['by_race_time', 'by_fastest_lap', 'by_consecutives'].find((key) => Array.isArray(leaderboard[key])) ||
    '';
  const rows = asRecordArray(leaderboard[primary]);

  const teamLeaderboard = toRecord(race.team_leaderboard);
  const teamMeta = toRecord(teamLeaderboard.meta);
  const teamPrimary =
    asString(teamMeta.primary_leaderboard) ||
    ['by_race_time', 'by_avg_fastest_lap', 'by_avg_consecutives'].find((key) => Array.isArray(teamLeaderboard[key])) ||
    '';

  return {
    race,
    meta,
    primary,
    rows,
    teamMeta,
    teamPrimary,
    teamRows: asRecordArray(teamLeaderboard[teamPrimary]),
  };
}

function heatNodeRows(payload: unknown): Dict[] {
  const heatNodes = toRecord(toRecord(payload).heatNodes);
  return Object.entries(heatNodes)
    .map(([nodeIndex, value]) => ({
      ...toRecord(value),
      node_index: Number(nodeIndex),
    }))
    .sort((a, b) => Number(a.node_index) - Number(b.node_index));
}

function firstRecordKeyCount(value: unknown): number {
  if (!isRecord(value)) {
    return 0;
  }
  return Object.keys(value).length;
}

function MiniMetric({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <div className={`demo-metric ${tone ? `tone-${tone}` : ''}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function EmptyState({ children }: { children: string }) {
  return <div className="demo-empty">{children}</div>;
}

function Demo() {
  const urlFromQuery = useMemo(() => {
    const queryUrl = new URLSearchParams(window.location.search).get('url');
    return queryUrl || DEFAULT_URL;
  }, []);

  const [url, setUrl] = useState(urlFromQuery);
  const [activeUrl, setActiveUrl] = useState(urlFromQuery);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionMessage, setConnectionMessage] = useState('Connecting');
  const [datasets, setDatasets] = useState<Record<string, DatasetEntry>>({});
  const [heartbeat, setHeartbeat] = useState<DatasetEntry | null>(null);
  const [serverClock, setServerClock] = useState<ClockSample | null>(null);
  const [now, setNow] = useState(Date.now());
  const [lastLoadAt, setLastLoadAt] = useState<string | null>(null);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);

  const clientRef = useRef<RotorHazardClient | null>(null);

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 250);
    return () => window.clearInterval(timer);
  }, []);

  const requestServerTime = async (client: RotorHazardClient | null) => {
    if (!client?.connected) {
      return;
    }

    const requestedAt = Date.now();
    const response = await client
      .emitRaw('get_server_time', null, { expectAck: true, timeoutMs: 2500 })
      .catch(() => undefined);
    const serverTimeS = asNumber(toRecord(response).server_time_s);

    if (serverTimeS !== null) {
      setServerClock({
        localAt: requestedAt,
        serverTimeS,
      });
    }
  };

  const requestLoadData = async () => {
    const client = clientRef.current;
    if (!client?.connected) {
      setConnectionMessage('Socket not connected');
      return;
    }

    setLastLoadAt(new Date().toISOString());
    await client.emitRaw('load_data', { load_types: [...BASELINE_LOAD_TYPES] }).catch((error: unknown) => {
      setConnectionMessage(error instanceof Error ? error.message : 'load_data failed');
    });
    void client.emitRaw('get_race_scheduled', null).catch(() => undefined);
    void requestServerTime(client);
  };

  useEffect(() => {
    let mounted = true;
    const client = new RotorHazardClient({
      url: activeUrl,
      autoConnect: false,
      autoJoinCluster: true,
      consoleLogging: false,
      quietEvents: ['heartbeat'],
      timeoutMs: 5000,
      onEvent: (event) => {
        if (!mounted) {
          return;
        }

        if (event.event === 'connect') {
          setIsConnected(true);
          setConnectionMessage('Connected');
          return;
        }

        if (event.event === 'disconnect') {
          setIsConnected(false);
          setConnectionMessage('Disconnected');
          return;
        }

        const payload = eventPayload(event);

        if (event.event === 'heartbeat') {
          setHeartbeat((previous) => ({
            event: event.event,
            payload,
            updatedAt: event.ts,
            count: (previous?.count ?? 0) + 1,
          }));
          return;
        }

        setDatasets((previous) => ({
          ...previous,
          [event.event]: {
            event: event.event,
            payload,
            updatedAt: event.ts,
            count: (previous[event.event]?.count ?? 0) + 1,
          },
        }));

        if (LIVE_ANNOUNCEMENT_EVENTS.has(event.event)) {
          setAnnouncements((previous) => [
            {
              id: event.id,
              event: event.event,
              message: summarizeAnnouncement(event.event, payload),
              at: event.ts,
            },
            ...previous,
          ].slice(0, 8));
        }
      },
    });

    clientRef.current = client;
    setDatasets({});
    setHeartbeat(null);
    setServerClock(null);
    setAnnouncements([]);
    setLastLoadAt(null);
    setIsConnected(false);
    setConnectionMessage('Connecting');

    client
      .connect()
      .then(() => {
        if (!mounted) {
          return;
        }
        void requestServerTime(client);
        void requestLoadData();
      })
      .catch((error: unknown) => {
        if (!mounted) {
          return;
        }
        setIsConnected(false);
        setConnectionMessage(error instanceof Error ? error.message : 'Connection failed');
      });

    return () => {
      mounted = false;
      client.disconnect().catch(() => undefined);
      if (clientRef.current === client) {
        clientRef.current = null;
      }
    };
  }, [activeUrl]);

  useEffect(() => {
    if (!isConnected) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      void requestServerTime(clientRef.current);
    }, 5000);

    return () => window.clearInterval(timer);
  }, [isConnected]);

  const raceStatus = recordDataset(datasets, 'race_status');
  const currentHeat = recordDataset(datasets, 'current_heat');
  const leaderboardPayload = dataset(datasets, 'leaderboard');
  const currentLaps = toRecord(toRecord(dataset(datasets, 'current_laps')).current);
  const pilotRows = rowsFromPayload(dataset(datasets, 'pilot_data'), 'pilots');
  const heatRows = rowsFromPayload(dataset(datasets, 'heat_data'), 'heats');
  const classRows = rowsFromPayload(dataset(datasets, 'class_data'), 'classes');
  const formatRows = rowsFromPayload(dataset(datasets, 'format_data'), 'formats');
  const seatRows = rowsFromPayload(dataset(datasets, 'seat_data'), 'seats');
  const frequencyRows = rowsFromPayload(dataset(datasets, 'frequency_data'), 'fdata');
  const lapNodes = asRecordArray(currentLaps.node_index);
  const heatNodes = heatNodeRows(currentHeat);
  const nodeData = recordDataset(datasets, 'node_data');
  const heartbeatPayload = toRecord(heartbeat?.payload);
  const leaderboard = getLeaderboard(leaderboardPayload);

  const currentHeatId = asNumber(raceStatus.race_heat_id) ?? asNumber(currentHeat.current_heat);
  const currentClassId = asNumber(raceStatus.race_class_id) ?? asNumber(currentHeat.heat_class);
  const currentFormatId = asNumber(raceStatus.race_format_id) ?? asNumber(currentHeat.heat_format);
  const activeHeat = findById(heatRows, currentHeatId, ['id', 'heat_id']);
  const activeClass = findById(classRows, currentClassId, ['id', 'class_id']);
  const activeFormat = findById(formatRows, currentFormatId, ['id', 'format_id']);
  const roundNumber = asNumber(raceStatus.next_round) ?? asNumber(currentHeat.next_round) ?? asNumber(leaderboard.race.round);
  const loadedCount = DATASET_EVENTS.filter((event) => datasets[event]).length;
  const serverNowS = serverClock ? serverClock.serverTimeS + (now - serverClock.localAt) / 1000 : null;
  const raceStartS = asNumber(raceStatus.pi_starts_at_s);
  const raceTimeS = asNumber(raceStatus.race_time_sec);
  const raceState = asNumber(raceStatus.race_status);
  const elapsedS = serverNowS !== null && raceStartS !== null ? Math.max(0, serverNowS - raceStartS) : null;
  const timerS =
    raceState === RACE_STATUS.STAGING && serverNowS !== null && raceStartS !== null
      ? raceStartS - serverNowS
      : raceState === RACE_STATUS.RACING && raceStatus.unlimited_time ? elapsedS
      : raceState === RACE_STATUS.RACING && raceTimeS !== null && elapsedS !== null
        ? raceTimeS - elapsedS
        : elapsedS;
  const raceTitle =
    displayValue(activeHeat?.displayname, '') ||
    displayValue(leaderboard.race.displayname, '') ||
    (currentHeatId ? `Heat ${currentHeatId}` : 'Practice Mode');

  const pilotById = useMemo(() => {
    const pilots = new Map<number, Dict>();
    pilotRows.forEach((pilot) => {
      const id = asNumber(pilot.pilot_id);
      if (id !== null) {
        pilots.set(id, pilot);
      }
    });
    return pilots;
  }, [pilotRows]);

  const laneCount = Math.max(lapNodes.length, heatNodes.length, frequencyRows.length, seatRows.length);
  const lanes = Array.from({ length: laneCount }, (_, nodeIndex) => {
    const heatNode = heatNodes.find((item) => asNumber(item.node_index) === nodeIndex) ?? {};
    const lapNode = lapNodes[nodeIndex] ?? {};
    const pilot = pilotById.get(asNumber(heatNode.pilot_id) ?? -1) ?? toRecord(lapNode.pilot);
    const laps = asRecordArray(lapNode.laps);
    return {
      nodeIndex,
      heatNode,
      lapNode,
      pilot,
      laps,
      lastLap: latestLap(laps),
      frequency: frequencyRows[nodeIndex] ?? {},
      seat: seatRows[nodeIndex] ?? {},
      currentRssi: asArray(heartbeatPayload.current_rssi)[nodeIndex],
      loopTime: asArray(heartbeatPayload.loop_time)[nodeIndex],
      peakRssi: asArray(nodeData.node_peak_rssi)[nodeIndex],
      enterAt: asArray(toRecord(dataset(datasets, 'enter_and_exit_at_levels')).enter_at_levels)[nodeIndex],
      exitAt: asArray(toRecord(dataset(datasets, 'enter_and_exit_at_levels')).exit_at_levels)[nodeIndex],
    };
  });

  const submitUrl = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setActiveUrl(url);
  };

  return (
    <main className="demo-page">
      <section className="demo-topbar">
        <a href="/" className="demo-brand">
          DronlyWork
        </a>
        <form onSubmit={submitUrl} className="demo-connect">
          <label>
            Socket URL
            <input value={url} onChange={(event) => setUrl(event.target.value)} />
          </label>
          <button type="submit" disabled={url === activeUrl}>
            Apply
          </button>
          <button type="button" onClick={() => void requestLoadData()} disabled={!isConnected}>
            Reload
          </button>
        </form>
        <div className={`demo-connection ${isConnected ? 'online' : 'offline'}`}>
          <span />
          {connectionMessage}
        </div>
      </section>

      <section className={`demo-race-hero state-${statusClass(raceStatus.race_status)}`}>
        <div className="race-identity">
          <span className="eyebrow">{raceStatusLabel(raceStatus.race_status)}</span>
          <h1>{raceTitle}</h1>
          <div className="race-subtitle">
            <span>{displayValue(activeClass?.displayname, 'No class')}</span>
            <span>{displayValue(activeFormat?.name, 'No format')}</span>
            <span>{roundNumber ? `Round ${roundNumber}` : 'Round pending'}</span>
          </div>
        </div>
        <div className="race-clock">
          <span>{raceState === RACE_STATUS.STAGING ? 'Starts In' : raceStatus.unlimited_time ? 'Elapsed' : 'Clock'}</span>
          <strong>{formatDuration(timerS)}</strong>
        </div>
        <div className="race-metrics">
          <MiniMetric label="Pilots" value={String(pilotRows.length)} tone="blue" />
          <MiniMetric label="Heats" value={String(heatRows.length)} tone="amber" />
          <MiniMetric label="Nodes" value={String(laneCount)} tone="green" />
          <MiniMetric label="Loaded" value={`${loadedCount}/${DATASET_EVENTS.length}`} tone="red" />
        </div>
      </section>

      <section className="demo-coverage" aria-label="load_data coverage">
        {DATASET_CATALOG.map((item) => {
          const entry = datasets[item.event];
          return (
            <span key={item.event} className={entry ? 'ready' : ''} title={item.event}>
              <b>{item.label}</b>
              <small>{entry ? new Date(entry.updatedAt).toLocaleTimeString() : 'waiting'}</small>
            </span>
          );
        })}
      </section>

      <section className="demo-grid primary-grid">
        <section className="demo-section leaderboard-section">
          <div className="section-title">
            <div>
              <span>Live Race</span>
              <h2>Leaderboard</h2>
            </div>
            <strong>{leaderboard.primary || 'pending'}</strong>
          </div>
          {leaderboard.rows.length ? (
            <div className="table-wrap">
              <table className="demo-table leaderboard-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Pilot</th>
                    <th>Team</th>
                    <th>Laps</th>
                    <th>Total</th>
                    <th>Average</th>
                    <th>Fastest</th>
                    <th>Consecutive</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.rows.map((row, index) => (
                    <tr key={`${displayValue(row.pilot_id, index)}-${index}`} className={index === 0 ? 'leader' : ''}>
                      <td>{displayValue(row.position, String(index + 1))}</td>
                      <td>
                        <strong>{displayValue(row.callsign, displayValue(row.name, 'Pilot'))}</strong>
                      </td>
                      <td>{displayValue(row.team_name)}</td>
                      <td>{displayValue(row.laps)}</td>
                      <td>{displayValue(row.total_time)}</td>
                      <td>{displayValue(row.average_lap)}</td>
                      <td>{displayValue(row.fastest_lap)}</td>
                      <td>{row.consecutives ? `${displayValue(row.consecutives_base)}/${displayValue(row.consecutives)}` : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState>Waiting for leaderboard data</EmptyState>
          )}

          {leaderboard.teamRows.length > 0 && (
            <div className="team-board">
              <h3>Teams</h3>
              <div className="table-wrap">
                <table className="demo-table compact">
                  <thead>
                    <tr>
                      <th>Rank</th>
                      <th>Team</th>
                      <th>Contributors</th>
                      <th>Laps</th>
                      <th>Average</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leaderboard.teamRows.map((row, index) => (
                      <tr key={`${displayValue(row.name, index)}-${index}`}>
                        <td>{displayValue(row.position, String(index + 1))}</td>
                        <td>{displayValue(row.name)}</td>
                        <td>
                          {displayValue(row.contributing)}/{displayValue(row.members)}
                        </td>
                        <td>{displayValue(row.laps)}</td>
                        <td>{displayValue(row.average_lap, displayValue(row.average_fastest_lap))}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </section>

        <section className="demo-section announcer-section">
          <div className="section-title">
            <div>
              <span>Race Audio</span>
              <h2>Callouts</h2>
            </div>
            <strong>{heartbeat ? `Heartbeat ${heartbeat.count}` : 'No heartbeat'}</strong>
          </div>
          {announcements.length ? (
            <div className="announcement-list">
              {announcements.map((announcement) => (
                <article key={`${announcement.id}-${announcement.event}`}>
                  <time>{new Date(announcement.at).toLocaleTimeString()}</time>
                  <strong>{announcement.message}</strong>
                  <span>{announcement.event}</span>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState>No race callouts yet</EmptyState>
          )}
          <div className="last-load">
            <span>Last load_data</span>
            <strong>{lastLoadAt ? new Date(lastLoadAt).toLocaleTimeString() : 'pending'}</strong>
          </div>
        </section>
      </section>

      <section className="demo-section lane-section">
        <div className="section-title">
          <div>
            <span>Current Heat</span>
            <h2>Viewer Lanes</h2>
          </div>
          <strong>{lanes.length ? `${lanes.length} lanes` : 'pending'}</strong>
        </div>
        {lanes.length ? (
          <div className="lane-grid">
            {lanes.map((lane) => {
              const color = displayValue(lane.heatNode.pilotColor, displayValue(lane.heatNode.activeColor, displayValue(lane.seat.color, '#3b82f6')));
              return (
                <article key={lane.nodeIndex} className="lane-card" style={{ '--lane-color': color } as CSSProperties}>
                  <div className="lane-head">
                    <span>Node {lane.nodeIndex + 1}</span>
                    <strong>{displayValue(lane.pilot.callsign, displayValue(lane.heatNode.callsign, 'Open'))}</strong>
                  </div>
                  <div className="lane-meta">
                    <span>
                      {displayValue(lane.frequency.band)}
                      {displayValue(lane.frequency.channel, '')} {displayValue(lane.frequency.frequency, 'No freq')}
                    </span>
                    <span>{lane.lapNode.finished_flag ? 'Finished' : `${lane.laps.length} laps`}</span>
                  </div>
                  <div className="lane-stats">
                    <MiniMetric label="Last" value={displayValue(lane.lastLap?.lap_time_formatted)} />
                    <MiniMetric label="RSSI" value={displayValue(lane.currentRssi, displayValue(lane.peakRssi))} />
                    <MiniMetric label="Enter/Exit" value={`${displayValue(lane.enterAt)}/${displayValue(lane.exitAt)}`} />
                  </div>
                  <div className="lap-strip" aria-label={`Node ${lane.nodeIndex + 1} laps`}>
                    {lane.laps.slice(-10).map((lap, index) => (
                      <span
                        key={`${displayValue(lap.lap_index, index)}-${index}`}
                        className={lap.deleted ? 'deleted' : lap.late_lap ? 'late' : ''}
                        title={`${displayValue(lap.lap_number)} ${displayValue(lap.lap_time_formatted)}`}
                      >
                        {displayValue(lap.lap_number, String(index + 1))}
                      </span>
                    ))}
                    {!lane.laps.length && <em>No laps</em>}
                  </div>
                </article>
              );
            })}
          </div>
        ) : (
          <EmptyState>Waiting for current heat data</EmptyState>
        )}
      </section>

      <section className="demo-grid two-column">
        <section className="demo-section">
          <div className="section-title">
            <div>
              <span>Event Setup</span>
              <h2>Pilots</h2>
            </div>
            <strong>{pilotRows.length}</strong>
          </div>
          {pilotRows.length ? (
            <div className="pilot-grid">
              {pilotRows.map((pilot, index) => (
                <article
                  key={`${displayValue(pilot.pilot_id, index)}-${index}`}
                  className="pilot-card"
                  style={{ '--pilot-color': displayValue(pilot.color, '#64748b') } as CSSProperties}
                >
                  <span>{displayValue(pilot.callsign, 'Pilot')}</span>
                  <strong>{displayValue(pilot.name, 'No name')}</strong>
                  <small>
                    Team {displayValue(pilot.team, '-')} / active {truthyLabel(pilot.active)}
                  </small>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState>Waiting for pilot data</EmptyState>
          )}
        </section>

        <section className="demo-section">
          <div className="section-title">
            <div>
              <span>Event Setup</span>
              <h2>Heats</h2>
            </div>
            <strong>{heatRows.length}</strong>
          </div>
          {heatRows.length ? (
            <div className="table-wrap tall">
              <table className="demo-table compact">
                <thead>
                  <tr>
                    <th>Heat</th>
                    <th>Class</th>
                    <th>Slots</th>
                    <th>Round</th>
                    <th>Active</th>
                  </tr>
                </thead>
                <tbody>
                  {heatRows.map((heat, index) => {
                    const heatClass = findById(classRows, heat.class_id, ['id', 'class_id']);
                    return (
                      <tr key={`${displayValue(heat.id, index)}-${index}`} className={asNumber(heat.id) === currentHeatId ? 'selected-row' : ''}>
                        <td>
                          <strong>{displayValue(heat.displayname, displayValue(heat.name))}</strong>
                        </td>
                        <td>{displayValue(heatClass?.displayname, displayValue(heat.class_id))}</td>
                        <td>{asArray(heat.slots).length}</td>
                        <td>{displayValue(heat.next_round)}</td>
                        <td>{truthyLabel(heat.active)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState>Waiting for heat data</EmptyState>
          )}
        </section>
      </section>

      <section className="demo-grid two-column">
        <section className="demo-section">
          <div className="section-title">
            <div>
              <span>Event Setup</span>
              <h2>Classes And Formats</h2>
            </div>
            <strong>
              {classRows.length}/{formatRows.length}
            </strong>
          </div>
          <div className="split-list">
            <div>
              <h3>Classes</h3>
              {classRows.length ? (
                classRows.map((raceClass, index) => (
                  <article key={`${displayValue(raceClass.id, index)}-${index}`} className={asNumber(raceClass.id) === currentClassId ? 'selected-card' : ''}>
                    <strong>{displayValue(raceClass.displayname, displayValue(raceClass.name))}</strong>
                    <span>{displayValue(raceClass.rank_method_label, `Format ${displayValue(raceClass.format)}`)}</span>
                  </article>
                ))
              ) : (
                <EmptyState>No classes loaded</EmptyState>
              )}
            </div>
            <div>
              <h3>Formats</h3>
              {formatRows.length ? (
                formatRows.map((format, index) => (
                  <article key={`${displayValue(format.id, index)}-${index}`} className={asNumber(format.id) === currentFormatId ? 'selected-card' : ''}>
                    <strong>{displayValue(format.name)}</strong>
                    <span>
                      {format.unlimited_time ? 'Unlimited' : `${displayValue(format.race_time_sec)}s`} / {displayValue(format.number_laps_win, 'open')} laps
                    </span>
                  </article>
                ))
              ) : (
                <EmptyState>No formats loaded</EmptyState>
              )}
            </div>
          </div>
        </section>

        <section className="demo-section">
          <div className="section-title">
            <div>
              <span>Timing</span>
              <h2>Hardware</h2>
            </div>
            <strong>{frequencyRows.length} freqs</strong>
          </div>
          <div className="hardware-grid">
            {frequencyRows.map((frequency, index) => (
              <article key={`${displayValue(frequency.frequency, index)}-${index}`}>
                <span>Node {index + 1}</span>
                <strong>
                  {displayValue(frequency.band)}
                  {displayValue(frequency.channel, '')}
                </strong>
                <small>{displayValue(frequency.frequency)} MHz</small>
              </article>
            ))}
          </div>
          <div className="settings-grid">
            <MiniMetric label="Profile" value={displayValue(recordDataset(datasets, 'node_tuning').profile_name)} />
            <MiniMetric label="Min Lap" value={`${displayValue(recordDataset(datasets, 'min_lap').min_lap)}s`} />
            <MiniMetric label="Lower Amount" value={displayValue(recordDataset(datasets, 'start_thresh_lower_amount').start_thresh_lower_amount)} />
            <MiniMetric label="Lower Duration" value={displayValue(recordDataset(datasets, 'start_thresh_lower_duration').start_thresh_lower_duration)} />
          </div>
          <div className="environment-list">
            {asArray(dataset(datasets, 'environmental_data')).length ? (
              asArray(dataset(datasets, 'environmental_data')).map((sensor, index) => (
                <pre key={index}>{formatJson(sensor)}</pre>
              ))
            ) : (
              <EmptyState>No environmental sensors</EmptyState>
            )}
          </div>
        </section>
      </section>

      <section className="demo-grid two-column">
        <section className="demo-section">
          <div className="section-title">
            <div>
              <span>Results</span>
              <h2>Race History</h2>
            </div>
            <strong>{objectValuesAsRecords(recordDataset(datasets, 'race_list').heats).length}</strong>
          </div>
          {objectValuesAsRecords(recordDataset(datasets, 'race_list').heats).length ? (
            <div className="table-wrap tall">
              <table className="demo-table compact">
                <thead>
                  <tr>
                    <th>Heat</th>
                    <th>Class</th>
                    <th>Rounds</th>
                    <th>Latest Start</th>
                  </tr>
                </thead>
                <tbody>
                  {objectValuesAsRecords(recordDataset(datasets, 'race_list').heats).map((race, index) => {
                    const rounds = objectValuesAsRecords(race.rounds);
                    const latest = rounds[rounds.length - 1];
                    return (
                      <tr key={`${displayValue(race.heat_id, index)}-${index}`}>
                        <td>{displayValue(race.displayname, displayValue(race.heat_id))}</td>
                        <td>{displayValue(race.class_id)}</td>
                        <td>{rounds.length}</td>
                        <td>{displayValue(latest?.start_time_formatted)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <EmptyState>No saved race history loaded</EmptyState>
          )}
        </section>

        <section className="demo-section">
          <div className="section-title">
            <div>
              <span>System</span>
              <h2>Services</h2>
            </div>
            <strong>{displayValue(recordDataset(datasets, 'language').language, 'language')}</strong>
          </div>
          <div className="service-grid">
            <MiniMetric label="Plugins" value={String(rowsFromPayload(dataset(datasets, 'plugin_list'), 'plugins').length)} />
            <MiniMetric label="Exporters" value={String(rowsFromPayload(dataset(datasets, 'exporter_list'), 'exporters').length)} />
            <MiniMetric label="Importers" value={String(rowsFromPayload(dataset(datasets, 'importer_list'), 'importers').length)} />
            <MiniMetric label="Generators" value={String(rowsFromPayload(dataset(datasets, 'heatgenerator_list'), 'generators').length)} />
            <MiniMetric label="VRx" value={truthyLabel(recordDataset(datasets, 'vrx_list').enabled)} />
            <MiniMetric label="Cluster" value={firstRecordKeyCount(dataset(datasets, 'cluster_status')) ? 'online' : 'single'} />
          </div>
          <div className="callout-pills">
            {asArray(dataset(datasets, 'callouts')).slice(0, 16).map((callout, index) => (
              <span key={`${asString(callout, String(index))}-${index}`}>{asString(callout, `Callout ${index + 1}`)}</span>
            ))}
            {!asArray(dataset(datasets, 'callouts')).length && <span>No saved callouts</span>}
          </div>
        </section>
      </section>

      <section className="demo-section data-library">
        <div className="section-title">
          <div>
            <span>load_data</span>
            <h2>Snapshot Library</h2>
          </div>
          <strong>{loadedCount} ready</strong>
        </div>
        <div className="snapshot-grid">
          {DATASET_CATALOG.map((item) => {
            const entry = datasets[item.event];
            return (
              <details key={item.event} className={entry ? 'ready' : ''}>
                <summary>
                  <span>
                    <strong>{item.label}</strong>
                    <small>{item.group}</small>
                  </span>
                  <b>{entry ? `${entry.count}x` : 'waiting'}</b>
                </summary>
                {entry ? <pre>{formatJson(entry.payload)}</pre> : <EmptyState>No payload received</EmptyState>}
              </details>
            );
          })}
        </div>
      </section>
    </main>
  );
}

export default Demo;

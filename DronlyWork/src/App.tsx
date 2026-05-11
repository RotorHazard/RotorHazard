import { useEffect, useMemo, useRef, useState } from 'react';
import {
  BASELINE_LOAD_TYPES,
  DEFAULT_MARKED_ENDPOINT_IDS,
  TODO_ENDPOINTS,
  type EndpointDefinition,
} from './lib/endpoints';
import { formatJson, type LogEntry, type ReceivedEvent, RotorHazardClient } from './lib/rhClient';

const DEFAULT_URL = import.meta.env.VITE_RH_SOCKET_URL || 'http://localhost:5000';

interface HeartbeatState {
  count: number;
  lastAt: string | null;
  payload?: unknown;
}

type EndpointStatus = 'idle' | 'running' | 'ok' | 'sent' | 'missing' | 'blocked' | 'error';

interface EndpointRunState {
  status: EndpointStatus;
  message: string;
  ts: string;
}

function parsePayload(text: string): unknown {
  if (!text.trim()) {
    return undefined;
  }
  return JSON.parse(text);
}

function summarizeHeartbeat(payload: unknown): string {
  if (!payload || typeof payload !== 'object') {
    return 'waiting';
  }

  const data = payload as Record<string, unknown>;
  const currentRssi = Array.isArray(data.current_rssi) ? data.current_rssi.length : 0;
  const frequency = Array.isArray(data.frequency) ? data.frequency.length : 0;
  const loopTime = Array.isArray(data.loop_time) ? data.loop_time.length : 0;
  const crossing = Array.isArray(data.crossing_flag) ? data.crossing_flag.length : 0;

  return `rssi ${currentRssi} / freq ${frequency} / loop ${loopTime} / crossing ${crossing}`;
}

function App() {
  const [url, setUrl] = useState(DEFAULT_URL);
  const [activeUrl, setActiveUrl] = useState(DEFAULT_URL);
  const [isConnected, setIsConnected] = useState(false);
  const [allowMutations, setAllowMutations] = useState(false);
  const [selectedId, setSelectedId] = useState('load_data');
  const [markedEndpointIds, setMarkedEndpointIds] = useState<Set<string>>(
    () => new Set(DEFAULT_MARKED_ENDPOINT_IDS),
  );
  const [payloadText, setPayloadText] = useState('');
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [events, setEvents] = useState<ReceivedEvent[]>([]);
  const [lastAck, setLastAck] = useState<unknown>(null);
  const [isCalling, setIsCalling] = useState(false);
  const [serverTime, setServerTime] = useState<number | null>(null);
  const [heartbeat, setHeartbeat] = useState<HeartbeatState>({ count: 0, lastAt: null });
  const [endpointResults, setEndpointResults] = useState<Record<string, EndpointRunState>>({});

  const clientRef = useRef<RotorHazardClient | null>(null);

  const selectedEndpoint = useMemo(
    () => TODO_ENDPOINTS.find((endpoint) => endpoint.id === selectedId) ?? TODO_ENDPOINTS[0],
    [selectedId],
  );

  const markedEndpoints = useMemo(
    () => TODO_ENDPOINTS.filter((endpoint) => markedEndpointIds.has(endpoint.id)),
    [markedEndpointIds],
  );

  const appendUiLog = (entry: Omit<LogEntry, 'id' | 'ts'>) => {
    setLogs((previous) => [
      ...previous.slice(-299),
      {
        id: Date.now() + Math.random(),
        ts: new Date().toISOString(),
        ...entry,
      },
    ]);
  };

  const setEndpointResult = (endpointId: string, status: EndpointStatus, message: string) => {
    setEndpointResults((previous) => ({
      ...previous,
      [endpointId]: {
        status,
        message,
        ts: new Date().toISOString(),
      },
    }));
  };

  const resultForEndpoint = (endpoint: EndpointDefinition) => endpointResults[endpoint.id];

  const resultFromCall = (
    endpoint: EndpointDefinition,
    result: Awaited<ReturnType<RotorHazardClient['callEndpoint']>>,
  ): Pick<EndpointRunState, 'status' | 'message'> => {
    if (endpoint.expectsAck) {
      if (result.ack === undefined) {
        return { status: 'missing', message: 'ACK missing or timed out' };
      }
      return { status: 'ok', message: 'ACK received' };
    }

    if (result.wait) {
      if (result.wait.missing.length) {
        return {
          status: 'missing',
          message: `Missing: ${result.wait.missing.join(', ')}`,
        };
      }
      return { status: 'ok', message: 'Expected events received' };
    }

    if (endpoint.action === 'connect' || endpoint.action === 'disconnect') {
      return { status: 'ok', message: 'Lifecycle action completed' };
    }

    return { status: 'sent', message: 'Event sent; no ACK or expected event configured' };
  };

  useEffect(() => {
    const client = new RotorHazardClient({
      url: activeUrl,
      autoConnect: false,
      autoJoinCluster: true,
      quietEvents: ['heartbeat'],
      timeoutMs: 3000,
      onLog: (entry) => {
        setLogs((previous) => [...previous.slice(-299), entry]);
      },
      onEvent: (event) => {
        if (event.event === 'heartbeat') {
          setHeartbeat((previous) => ({
            count: previous.count + 1,
            lastAt: event.ts,
            payload: event.args[0],
          }));
          return;
        }

        setEvents((previous) => [...previous.slice(-199), event]);
        const firstArg = event.args[0] as { server_time_s?: number } | undefined;
        if (event.event === 'server_time' && typeof firstArg?.server_time_s === 'number') {
          setServerTime(firstArg.server_time_s);
        }
      },
    });

    clientRef.current = client;
    setHeartbeat({ count: 0, lastAt: null });
    setEndpointResults({});

    const unsubscribeLog = client.onLog((entry) => {
      if (entry.direction === 'ack' && entry.event === 'get_server_time') {
        const ack = entry.data as { server_time_s?: number } | undefined;
        if (typeof ack?.server_time_s === 'number') {
          setServerTime(ack.server_time_s);
        }
      }
    });

    const unsubscribeEvent = client.onEvent((event) => {
      if (event.event === 'connect') {
        setIsConnected(true);
      }
      if (event.event === 'disconnect') {
        setIsConnected(false);
      }
    });

    return () => {
      unsubscribeLog();
      unsubscribeEvent();
      client.disconnect().catch((error: unknown) => {
        console.warn('[RH:client] disconnect during cleanup failed', error);
      });
      clientRef.current = null;
      setIsConnected(false);
    };
  }, [activeUrl]);

  useEffect(() => {
    setPayloadText(
      selectedEndpoint.defaultPayload === undefined ? '' : formatJson(selectedEndpoint.defaultPayload),
    );
    setLastAck(null);
  }, [selectedEndpoint]);

  const callEndpoint = async (
    endpoint: EndpointDefinition,
    overridePayloadText = payloadText,
    manageBusyState = true,
  ) => {
    const client = clientRef.current;
    if (!client) {
      return;
    }

    if (!endpoint.readOnly && !allowMutations) {
      appendUiLog({
        level: 'warn',
        direction: 'client',
        event: endpoint.id,
        message: 'Mutation blocked by UI toggle',
        data: endpoint,
      });
      setEndpointResult(endpoint.id, 'blocked', 'Mutation blocked');
      return;
    }

    setEndpointResult(endpoint.id, 'running', 'Running');
    if (manageBusyState) {
      setIsCalling(true);
    }
    try {
      const payload = endpoint.action === 'emit' ? parsePayload(overridePayloadText) : undefined;
      const result = await client.callEndpoint(endpoint, payload, 3500);
      setLastAck(result.ack ?? null);
      const nextResult = resultFromCall(endpoint, result);
      setEndpointResult(endpoint.id, nextResult.status, nextResult.message);
    } catch (error) {
      setEndpointResult(endpoint.id, 'error', error instanceof Error ? error.message : 'Unknown endpoint call error');
      appendUiLog({
        level: 'error',
        direction: 'error',
        event: endpoint.id,
        message: error instanceof Error ? error.message : 'Unknown endpoint call error',
        data: error,
      });
    } finally {
      if (manageBusyState) {
        setIsCalling(false);
      }
      setIsConnected(client.connected);
    }
  };

  const payloadTextForEndpoint = (endpoint: EndpointDefinition) => {
    if (endpoint.id === selectedId) {
      return payloadText;
    }
    return endpoint.defaultPayload === undefined ? '' : formatJson(endpoint.defaultPayload);
  };

  const runMarkedEndpoints = async () => {
    if (!clientRef.current?.connected) {
      appendUiLog({
        level: 'warn',
        direction: 'client',
        event: 'run_marked',
        message: 'Marked endpoints skipped because socket is not connected',
      });
      return;
    }

    const runnableMarkedEndpoints = markedEndpoints.filter((endpoint) => endpoint.action === 'emit');

    appendUiLog({
      level: 'info',
      direction: 'client',
      event: 'run_marked',
      message: 'Running marked endpoints after connect',
      data: runnableMarkedEndpoints.map((endpoint) => endpoint.id),
    });

    setIsCalling(true);
    try {
      for (const endpoint of runnableMarkedEndpoints) {
        await callEndpoint(endpoint, payloadTextForEndpoint(endpoint), false);
      }
    } finally {
      setIsCalling(false);
    }
  };

  const connect = async () => {
    const connectEndpoint = TODO_ENDPOINTS.find((endpoint) => endpoint.id === 'connect')!;
    await callEndpoint(connectEndpoint, undefined, false);
    await runMarkedEndpoints();
  };

  const disconnect = () => {
    void callEndpoint(TODO_ENDPOINTS.find((endpoint) => endpoint.id === 'disconnect')!);
  };

  const loadEverything = () => {
    const endpoint = TODO_ENDPOINTS.find((item) => item.id === 'load_data')!;
    const payload = formatJson({ load_types: [...BASELINE_LOAD_TYPES] });
    setSelectedId(endpoint.id);
    setPayloadText(payload);
    void callEndpoint(endpoint, payload);
  };

  const applyUrl = () => {
    setEvents([]);
    setLogs([]);
    setLastAck(null);
    setEndpointResults({});
    setActiveUrl(url);
  };

  const toggleMarkedEndpoint = (endpointId: string) => {
    setMarkedEndpointIds((previous) => {
      const next = new Set(previous);
      if (next.has(endpointId)) {
        next.delete(endpointId);
      } else {
        next.add(endpointId);
      }
      return next;
    });
  };

  const markReadEndpoints = () => {
    setMarkedEndpointIds(
      new Set(
        TODO_ENDPOINTS
          .filter((endpoint) => endpoint.readOnly && endpoint.action === 'emit')
          .map((endpoint) => endpoint.id),
      ),
    );
  };

  const markAllEndpoints = () => {
    setMarkedEndpointIds(new Set(TODO_ENDPOINTS.filter((endpoint) => endpoint.action === 'emit').map((endpoint) => endpoint.id)));
  };

  const clearMarkedEndpoints = () => {
    setMarkedEndpointIds(new Set());
  };

  const latestEvents = [...events].reverse().slice(0, 30);
  const latestLogs = [...logs].reverse().slice(0, 120);

  return (
    <main>
      <header>
        <div>
          <h1>Dronly RotorHazard Socket Library</h1>
          <p>
            Status: <strong className={isConnected ? 'ok' : 'bad'}>{isConnected ? 'connected' : 'disconnected'}</strong>
          </p>
        </div>
        <div className="server-time">
          <div>{serverTime ? `Server monotonic: ${serverTime.toFixed(3)}s` : 'Server monotonic: none'}</div>
          <div className="heartbeat-pulse">
            <span className={heartbeat.lastAt ? 'pulse-dot active' : 'pulse-dot'} />
            <span>Heartbeat #{heartbeat.count}</span>
            <small>
              {heartbeat.lastAt
                ? `${new Date(heartbeat.lastAt).toLocaleTimeString()} | ${summarizeHeartbeat(heartbeat.payload)}`
                : 'waiting'}
            </small>
          </div>
        </div>
      </header>

      <section className="toolbar">
        <label>
          Socket URL
          <input value={url} onChange={(event) => setUrl(event.target.value)} />
        </label>
        <button onClick={applyUrl} disabled={isCalling || url === activeUrl}>
          Apply URL
        </button>
        <button onClick={() => void connect()} disabled={isCalling || isConnected}>
          Connect + marked ({markedEndpoints.length})
        </button>
        <button onClick={disconnect} disabled={isCalling || !isConnected}>
          Disconnect
        </button>
        <button onClick={loadEverything} disabled={isCalling || !isConnected}>
          Read load_data
        </button>
        <button onClick={() => void runMarkedEndpoints()} disabled={isCalling || !isConnected}>
          Run marked
        </button>
        <label className="check">
          <input
            type="checkbox"
            checked={allowMutations}
            onChange={(event) => setAllowMutations(event.target.checked)}
          />
          allow mutating endpoints
        </label>
      </section>

      <section className="layout">
        <aside>
          <div className="aside-head">
            <h2>TODO endpoints</h2>
            <span>{markedEndpoints.length} marked</span>
          </div>
          <div className="mark-actions">
            <button onClick={markReadEndpoints}>Mark reads</button>
            <button onClick={markAllEndpoints}>Mark all</button>
            <button onClick={clearMarkedEndpoints}>Clear</button>
          </div>
          <div className="endpoint-list">
            {TODO_ENDPOINTS.map((endpoint) => (
              <div
                key={endpoint.id}
                className={`endpoint-row ${endpoint.id === selectedId ? 'selected' : ''}`}
              >
                <input
                  type="checkbox"
                  checked={markedEndpointIds.has(endpoint.id)}
                  onChange={() => toggleMarkedEndpoint(endpoint.id)}
                  title="Run this endpoint after Connect"
                />
                <button type="button" onClick={() => setSelectedId(endpoint.id)}>
                  <span>{endpoint.todoName}</span>
                  <small>
                    {endpoint.readOnly ? 'read' : 'mutates'}
                    {resultForEndpoint(endpoint) && (
                      <b className={`status ${resultForEndpoint(endpoint)?.status}`}>
                        {resultForEndpoint(endpoint)?.status}
                      </b>
                    )}
                  </small>
                </button>
              </div>
            ))}
          </div>
        </aside>

        <section className="panel">
          <div className="endpoint-head">
            <div>
              <h2>{selectedEndpoint.label}</h2>
              <p>{selectedEndpoint.notes}</p>
            </div>
            <button
              onClick={() => void callEndpoint(selectedEndpoint)}
              disabled={isCalling || (!selectedEndpoint.readOnly && !allowMutations)}
            >
              Run
            </button>
          </div>

          <div className="meta">
            <span>TODO: {selectedEndpoint.todoName}</span>
            <span>Socket event: {selectedEndpoint.eventName ?? selectedEndpoint.action}</span>
            <span>{selectedEndpoint.expectsAck ? 'ACK expected' : 'no ACK'}</span>
            {resultForEndpoint(selectedEndpoint) && (
              <span className={`status ${resultForEndpoint(selectedEndpoint)?.status}`}>
                {resultForEndpoint(selectedEndpoint)?.message}
              </span>
            )}
          </div>

          <label>
            Payload JSON
            <textarea
              value={payloadText}
              onChange={(event) => setPayloadText(event.target.value)}
              spellCheck={false}
              disabled={selectedEndpoint.action !== 'emit'}
            />
          </label>

          <div>
            <h3>Expected read events</h3>
            <div className="chips">
              {selectedEndpoint.expectedEvents.length ? (
                selectedEndpoint.expectedEvents.map((event) => <span key={event}>{event}</span>)
              ) : (
                <span>ACK / lifecycle only</span>
              )}
            </div>
          </div>

          <div>
            <h3>Last ACK</h3>
            <pre>{lastAck === null ? 'none' : formatJson(lastAck)}</pre>
          </div>
        </section>

        <section className="panel">
          <div className="panel-head">
            <h2>Received events</h2>
            <button onClick={() => setEvents([])}>Clear</button>
          </div>
          <div className="stream">
            {latestEvents.map((event, idx) => (
              <article key={`${event.ts}-${event.id}-${idx}`}>
                <strong>{event.event}</strong>
                <time>{new Date(event.ts).toLocaleTimeString()}</time>
                <pre>{formatJson(event.args.length === 1 ? event.args[0] : event.args)}</pre>
              </article>
            ))}
          </div>
        </section>
      </section>

      <section className="panel logs">
        <div className="panel-head">
          <h2>Verbose library logs</h2>
          <button onClick={() => setLogs([])}>Clear</button>
        </div>
        <div className="log-list">
          {latestLogs.map((log, idx) => (
            <div key={`${log.ts}-${log.id}-${idx}`} className={`log ${log.level}`}>
              <time>{new Date(log.ts).toLocaleTimeString()}</time>
              <strong>{log.direction}</strong>
              <span>{log.event ?? '-'}</span>
              <p>{log.message}</p>
              {log.data !== undefined && <pre>{formatJson(log.data)}</pre>}
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}

export default App;

import { io, Socket } from 'socket.io-client';
import type { EndpointDefinition } from './endpoints';
import type { SocketEventName } from '../../types';

export type LogLevel = 'debug' | 'info' | 'warn' | 'error';
export type LogDirection = 'client' | 'out' | 'in' | 'ack' | 'wait' | 'error';

export interface LogEntry {
  id: number;
  ts: string;
  level: LogLevel;
  direction: LogDirection;
  event?: string;
  message: string;
  data?: unknown;
}

export interface ReceivedEvent {
  id: number;
  ts: string;
  event: string;
  args: unknown[];
}

export interface WaitResult {
  expected: string[];
  received: ReceivedEvent[];
  missing: string[];
  timedOut: boolean;
}

export interface EndpointCallResult {
  endpoint: EndpointDefinition;
  ack?: unknown;
  wait?: WaitResult;
}

export interface RotorHazardClientOptions {
  url: string;
  autoConnect?: boolean;
  autoJoinCluster?: boolean;
  consoleLogging?: boolean;
  quietEvents?: string[];
  timeoutMs?: number;
  onLog?: (entry: LogEntry) => void;
  onEvent?: (event: ReceivedEvent) => void;
}

type EventListener = (event: ReceivedEvent) => void;
type LogListener = (entry: LogEntry) => void;

export class RotorHazardClient {
  readonly socket: Socket;

  private eventSeq = 0;
  private logSeq = 0;
  private readonly timeoutMs: number;
  private readonly autoJoinCluster: boolean;
  private readonly consoleLogging: boolean;
  private readonly quietEvents: Set<string>;
  private readonly eventListeners = new Set<EventListener>();
  private readonly logListeners = new Set<LogListener>();
  private readonly eventHistory = new Map<string, ReceivedEvent[]>();

  constructor(options: RotorHazardClientOptions) {
    this.timeoutMs = options.timeoutMs ?? 2500;
    this.autoJoinCluster = options.autoJoinCluster ?? true;
    this.consoleLogging = options.consoleLogging ?? true;
    this.quietEvents = new Set(options.quietEvents ?? []);

    if (options.onLog) {
      this.logListeners.add(options.onLog);
    }
    if (options.onEvent) {
      this.eventListeners.add(options.onEvent);
    }

    this.socket = io(options.url, {
      autoConnect: options.autoConnect ?? false,
      transports: ['websocket', 'polling'],
    });

    this.attachSocketLogging(options.url);
  }

  get connected(): boolean {
    return this.socket.connected;
  }

  onLog(listener: LogListener): () => void {
    this.logListeners.add(listener);
    return () => this.logListeners.delete(listener);
  }

  onEvent(listener: EventListener): () => void {
    this.eventListeners.add(listener);
    return () => this.eventListeners.delete(listener);
  }

  getHistory(event?: string): ReceivedEvent[] {
    if (event) {
      return [...(this.eventHistory.get(event) ?? [])];
    }
    return [...this.eventHistory.values()].flat().sort((a, b) => a.id - b.id);
  }

  clearHistory(): void {
    this.log('info', 'client', undefined, 'Clearing received event history');
    this.eventHistory.clear();
  }

  connect(): Promise<void> {
    this.log('info', 'client', 'connect', 'Connecting to RotorHazard socket', {
      connected: this.socket.connected,
    });

    if (this.socket.connected) {
      this.log('debug', 'client', 'connect', 'Socket already connected');
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      const timeout = globalThis.setTimeout(() => {
        cleanup();
        reject(new Error(`Timed out connecting after ${this.timeoutMs}ms`));
      }, this.timeoutMs);

      const cleanup = () => {
        globalThis.clearTimeout(timeout);
        this.socket.off('connect', onConnect);
        this.socket.off('connect_error', onConnectError);
      };

      const onConnect = () => {
        cleanup();
        this.log('info', 'client', 'connect', 'Connect promise resolved');
        if (this.autoJoinCluster) {
          this.emitRaw('join_cluster', undefined, { expectAck: false }).catch((error: unknown) => {
            this.log('error', 'error', 'join_cluster', 'join_cluster emit failed', error);
          });
        }
        resolve();
      };

      const onConnectError = (error: Error) => {
        cleanup();
        this.log('error', 'error', 'connect', 'Connect promise rejected', error.message);
        reject(error);
      };

      this.socket.once('connect', onConnect);
      this.socket.once('connect_error', onConnectError);
      this.socket.connect();
    });
  }

  disconnect(): Promise<void> {
    this.log('info', 'client', 'disconnect', 'Disconnecting socket', {
      connected: this.socket.connected,
    });

    if (!this.socket.connected) {
      this.log('debug', 'client', 'disconnect', 'Socket already disconnected');
      return Promise.resolve();
    }

    return new Promise((resolve) => {
      const timeout = globalThis.setTimeout(() => {
        this.socket.off('disconnect', onDisconnect);
        resolve();
      }, this.timeoutMs);

      const onDisconnect = () => {
        globalThis.clearTimeout(timeout);
        this.socket.off('disconnect', onDisconnect);
        this.log('info', 'client', 'disconnect', 'Disconnect promise resolved');
        resolve();
      };

      this.socket.once('disconnect', onDisconnect);
      this.socket.disconnect();
    });
  }

  async callEndpoint(
    endpoint: EndpointDefinition,
    payload: unknown = endpoint.defaultPayload,
    timeoutMs = this.timeoutMs,
  ): Promise<EndpointCallResult> {
    this.log('info', 'client', endpoint.id, 'Calling endpoint definition', {
      endpoint,
      payload,
      timeoutMs,
    });

    if (endpoint.action === 'connect') {
      await this.connect();
      return { endpoint };
    }

    if (endpoint.action === 'disconnect') {
      await this.disconnect();
      return { endpoint };
    }

    if (!endpoint.eventName) {
      throw new Error(`Endpoint ${endpoint.id} has no eventName`);
    }

    const waitPromise = endpoint.expectedEvents.length
      ? this.waitForEvents(endpoint.expectedEvents, timeoutMs)
      : Promise.resolve<WaitResult | undefined>(undefined);

    const ack = await this.emitRaw(endpoint.eventName, payload, {
      expectAck: endpoint.expectsAck ?? false,
      timeoutMs,
    });
    const wait = await waitPromise;

    this.log('info', 'client', endpoint.id, 'Endpoint call finished', {
      ack,
      wait,
    });

    return { endpoint, ack, wait };
  }

  emitRaw(
    eventName: SocketEventName,
    payload?: unknown,
    options: { expectAck?: boolean; timeoutMs?: number } = {},
  ): Promise<unknown> {
    const timeoutMs = options.timeoutMs ?? this.timeoutMs;

    this.log('info', 'out', eventName, 'Emitting Socket.IO event', {
      payload,
      expectAck: options.expectAck ?? false,
    });

    if (!options.expectAck) {
      if (payload === undefined) {
        this.socket.emit(eventName);
      } else {
        this.socket.emit(eventName, payload);
      }
      return Promise.resolve(undefined);
    }

    return new Promise((resolve) => {
      const timeout = globalThis.setTimeout(() => {
        this.log('warn', 'wait', eventName, `ACK timed out after ${timeoutMs}ms`);
        resolve(undefined);
      }, timeoutMs);

      const ack = (response: unknown) => {
        globalThis.clearTimeout(timeout);
        this.log('info', 'ack', eventName, 'Received Socket.IO ACK', response);
        resolve(response);
      };

      this.socket.emit(eventName, payload ?? null, ack);
    });
  }

  waitForEvents(expectedEvents: string[], timeoutMs = this.timeoutMs): Promise<WaitResult> {
    const expected = [...new Set(expectedEvents)];
    const received: ReceivedEvent[] = [];
    const remaining = new Set(expected);

    this.log('debug', 'wait', undefined, 'Waiting for expected events', {
      expected,
      timeoutMs,
    });

    return new Promise((resolve) => {
      const cleanup = () => {
        globalThis.clearTimeout(timeout);
        this.eventListeners.delete(listener);
      };

      const finish = (timedOut: boolean) => {
        cleanup();
        const missing = [...remaining];
        const result = { expected, received, missing, timedOut };
        this.log(timedOut && missing.length ? 'warn' : 'info', 'wait', undefined, 'Event wait finished', result);
        resolve(result);
      };

      const timeout = globalThis.setTimeout(() => finish(true), timeoutMs);

      const listener: EventListener = (event) => {
        if (!remaining.has(event.event)) {
          return;
        }
        received.push(event);
        remaining.delete(event.event);
        this.log('debug', 'wait', event.event, 'Observed expected event', {
          remaining: [...remaining],
        });
        if (!remaining.size) {
          finish(false);
        }
      };

      this.eventListeners.add(listener);
    });
  }

  private attachSocketLogging(url: string): void {
    this.log('info', 'client', undefined, 'Creating RotorHazard socket client', { url });

    this.socket.on('connect', () => {
      this.recordEvent('connect', [this.socket.id]);
      this.log('info', 'client', 'connect', 'Socket connected', {
        id: this.socket.id,
        transport: this.socket.io.engine.transport.name,
      });
    });

    this.socket.on('disconnect', (reason) => {
      this.recordEvent('disconnect', [reason]);
      this.log('warn', 'client', 'disconnect', 'Socket disconnected', { reason });
    });

    this.socket.on('connect_error', (error) => {
      this.log('error', 'error', 'connect_error', 'Socket connect_error', {
        message: error.message,
      });
    });

    this.socket.io.on('reconnect_attempt', (attempt) => {
      this.log('warn', 'client', 'reconnect_attempt', 'Socket reconnect attempt', { attempt });
    });

    this.socket.io.on('reconnect', (attempt) => {
      this.log('info', 'client', 'reconnect', 'Socket reconnected', { attempt });
    });

    this.socket.onAny((event, ...args) => {
      this.recordEvent(event, args);
    });
  }

  private recordEvent(event: string, args: unknown[]): void {
    const entry: ReceivedEvent = {
      id: ++this.eventSeq,
      ts: new Date().toISOString(),
      event,
      args,
    };

    const existing = this.eventHistory.get(event) ?? [];
    this.eventHistory.set(event, [...existing.slice(-19), entry]);

    if (!this.quietEvents.has(event)) {
      this.log('info', 'in', event, 'Received Socket.IO event', args);
    }
    this.eventListeners.forEach((listener) => listener(entry));
  }

  private log(level: LogLevel, direction: LogDirection, event: string | undefined, message: string, data?: unknown): void {
    const entry: LogEntry = {
      id: ++this.logSeq,
      ts: new Date().toISOString(),
      level,
      direction,
      event,
      message,
      data,
    };

    if (this.consoleLogging) {
      const consoleMethod = level === 'error' ? console.error : level === 'warn' ? console.warn : console.log;
      consoleMethod(`[RH:${direction}]${event ? ` ${event}` : ''} ${message}`, data ?? '');
    }
    this.logListeners.forEach((listener) => listener(entry));
  }
}

export function formatJson(value: unknown): string {
  return JSON.stringify(value, null, 2);
}

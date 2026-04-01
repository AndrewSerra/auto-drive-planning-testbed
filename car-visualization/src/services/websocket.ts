
import type { PositionData, ActionObject } from '../reducers/positions';

const ServerState = {
  CONNECTED: 'CONNECTED',
  DISCONNECTED: 'DISCONNECTED',
} as const;

type ServerState = typeof ServerState[keyof typeof ServerState];

export class WebsocketService {
  #state: ServerState = ServerState.DISCONNECTED;
  #host: string;
  #id: string;
  #ws!: WebSocket;
  #intentionalClose = false;
  #dispatch: ((action: ActionObject) => void) | null = null;
  #connectionChangeHandler: ((state: ServerState) => void) | null = null;
  readonly #reconnectDelay = 2000;

  constructor(host: string) {
    this.#host = host;
    this.#id = crypto.randomUUID();
    this.#connect();
  }

  public get state(): ServerState { return this.#state; }

  public set dispatch(fn: ((action: ActionObject) => void) | null) {
    this.#dispatch = fn;
  }

  public set onconnectionchange(handler: ((state: ServerState) => void) | null) {
    this.#connectionChangeHandler = handler;
  }

  public close(): void {
    this.#intentionalClose = true;
    this.#ws.close();
  }

  #connect(): void {
    this.#ws = new WebSocket(this.#host);
    this.#ws.onopen = () => this.#onConnect();
    this.#ws.onclose = () => this.#onDisconnect();
    this.#ws.onmessage = (e) => this.#handleMessage(e);
  }

  #handleMessage(event: MessageEvent): void {
    if (!this.#dispatch) return;
    let parsed: unknown;
    try { parsed = JSON.parse(event.data); } catch { return; }
    if (typeof parsed !== 'object' || parsed === null) return;
    const msg = parsed as Record<string, unknown>;
    if ('is_success' in msg) return;
    switch (msg.type) {
      case 'NEW_POSITION':
        this.#dispatch({ type: 'NEW_POSITION', data: msg.data as PositionData }); break;
      case 'SYSTEM_HALT':
        this.#dispatch({ type: 'SYSTEM_HALT' }); break;
      case 'SYSTEM_RESUME':
        this.#dispatch({ type: 'SYSTEM_RESUME' }); break;
    }
  }

  #onConnect(): void {
    this.#state = ServerState.CONNECTED;
    this.#ws.send(JSON.stringify({
      action: 'INITIALIZE',
      id: this.#id,
      connection_type: 'display',
    }));
    this.#connectionChangeHandler?.(ServerState.CONNECTED);
    console.log(`[ws] registered as display '${this.#id}'`);
  }

  #onDisconnect(): void {
    this.#state = ServerState.DISCONNECTED;
    this.#connectionChangeHandler?.(ServerState.DISCONNECTED);
    console.log('[ws] disconnected');
    if (!this.#intentionalClose) {
      console.log(`[ws] reconnecting in ${this.#reconnectDelay}ms...`);
      setTimeout(() => this.#connect(), this.#reconnectDelay);
    }
  }
}

import { useEffect, useReducer, useRef, useState, createContext, useContext } from 'react';
import { positionReducer, type StateObject } from './reducers/positions';
import { WebsocketService } from './services/websocket';
import { DemoService } from './services/demo';

const WS_URL = (import.meta as { env: Record<string, string> }).env.VITE_WS_URL ?? 'ws://localhost:8765';
const DEMO_MODE = (import.meta as { env: Record<string, string> }).env.VITE_DEMO === 'true';

const COLOR_PALETTE = [
  '#e6194b', '#3cb44b', '#4363d8', '#f58231',
  '#911eb4', '#42d4f4', '#f032e6', '#bfef45',
  '#fabed4', '#469990',
];

const WORLD_MIN_X = -50, WORLD_MAX_X = 50;
const WORLD_MIN_Y = -50, WORLD_MAX_Y = 50;

// ---- Context ----

type AppContextValue = {
  state: StateObject;
  colorMap: Map<string, string>;
  connectionStatus: 'CONNECTED' | 'DISCONNECTED';
};

const AppContext = createContext<AppContextValue | null>(null);

function useAppContext(): AppContextValue {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error('useAppContext must be used inside AppContext.Provider');
  return ctx;
}

// ---- Sidebar ----

function Sidebar() {
  const { state, colorMap, connectionStatus } = useAppContext();
  const connected = connectionStatus === 'CONNECTED';
  const running = state.system === 'RUNNING';
  const carIDs = Object.keys(state.positions);

  return (
    <div style={{
      width: '220px',
      minWidth: '220px',
      height: '100%',
      backgroundColor: '#1a1a2e',
      color: '#e0e0e0',
      display: 'flex',
      flexDirection: 'column',
      padding: '16px',
      boxSizing: 'border-box',
      gap: '12px',
      fontFamily: 'sans-serif',
    }}>
      {/* Connection indicator */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '14px' }}>
        <span style={{
          color: connected ? '#4caf50' : '#f44336',
          animation: connected ? 'none' : 'pulse 1.2s ease-in-out infinite',
        }}>●</span>
        <span style={{ color: connected ? '#4caf50' : '#f44336', fontWeight: 600 }}>
          {connectionStatus}
        </span>
      </div>

      {/* System status */}
      <div style={{
        fontSize: '13px',
        fontWeight: 700,
        letterSpacing: '0.05em',
        color: running ? '#4caf50' : '#f44336',
      }}>
        SYSTEM {running ? 'RUNNING' : 'HALTED'}
      </div>

      {/* Active cars label */}
      <div style={{ fontSize: '12px', color: '#9e9e9e', fontWeight: 600, letterSpacing: '0.08em' }}>
        ACTIVE CARS ({carIDs.length})
      </div>

      {/* Car legend */}
      <div style={{ overflowY: 'auto', flex: 1, display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {carIDs.map((id) => (
          <div key={id} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              backgroundColor: colorMap.get(id) ?? '#888',
              flexShrink: 0,
              opacity: state.positions[id].inbounds ? 1 : 0.35,
            }} />
            <span style={{
              fontFamily: 'monospace',
              fontSize: '12px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              opacity: state.positions[id].inbounds ? 1 : 0.35,
            }}>
              {id}
            </span>
          </div>
        ))}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.2; }
        }
      `}</style>
    </div>
  );
}

// ---- BirdsEyeView ----

function BirdsEyeView() {
  const { state, colorMap } = useAppContext();
  const { positions } = state;
  const viewWidth = WORLD_MAX_X - WORLD_MIN_X;
  const viewHeight = WORLD_MAX_Y - WORLD_MIN_Y;

  return (
    <div style={{ flex: 1, height: '100%', backgroundColor: '#0d0d1a', overflow: 'hidden' }}>
      <svg
        width="100%"
        height="100%"
        viewBox={`${WORLD_MIN_X} ${WORLD_MIN_Y} ${viewWidth} ${viewHeight}`}
        preserveAspectRatio="xMidYMid meet"
      >
        {/* Grid crosshairs */}
        <line x1="0" y1={WORLD_MIN_Y} x2="0" y2={WORLD_MAX_Y} stroke="#333" strokeWidth="0.5" />
        <line x1={WORLD_MIN_X} y1="0" x2={WORLD_MAX_X} y2="0" stroke="#333" strokeWidth="0.5" />

        {/* Car circles (Y-flipped) */}
        <g transform={`scale(1,-1)`}>
          {Object.entries(positions).map(([id, { posX, posY, inbounds }]) => (
            <circle
              key={id}
              cx={posX}
              cy={posY}
              r={1.5}
              fill={colorMap.get(id) ?? '#888'}
              opacity={inbounds ? 1 : 0.35}
            />
          ))}
        </g>

        {/* Car labels (unflipped) */}
        <g>
          {Object.entries(positions).map(([id, { posX, posY, inbounds }]) => (
            <text
              key={id}
              x={posX + 2}
              y={WORLD_MIN_Y + WORLD_MAX_Y - posY}
              fontSize="3"
              fill={colorMap.get(id) ?? '#888'}
              opacity={inbounds ? 1 : 0.35}
              fontFamily="monospace"
            >
              {id}
            </text>
          ))}
        </g>
      </svg>
    </div>
  );
}

// ---- App ----

function App() {
  const [state, dispatch] = useReducer(positionReducer, { system: 'RUNNING', positions: {} });
  const [connStatus, setConnStatus] = useState<'CONNECTED' | 'DISCONNECTED'>('DISCONNECTED');
  const colorMapRef = useRef<Map<string, string>>(new Map());

  useEffect(() => {
    const ws = DEMO_MODE ? new DemoService() : new WebsocketService(WS_URL);

    ws.dispatch = dispatch;
    ws.onconnectionchange = (s) => setConnStatus(s);

    return () => {
      ws.onconnectionchange = null;
      ws.dispatch = null;
      ws.close();
    };
  }, []);

  useEffect(() => {
    const map = colorMapRef.current;
    Object.keys(state.positions).forEach((id) => {
      if (!map.has(id)) map.set(id, COLOR_PALETTE[map.size % COLOR_PALETTE.length]);
    });
  }, [state.positions]);

  return (
    <AppContext.Provider value={{ state, colorMap: colorMapRef.current, connectionStatus: connStatus }}>
      <div style={{
        display: 'flex',
        flexDirection: 'row',
        width: '100%',
        height: '100svh',
        textAlign: 'left',
        boxSizing: 'border-box',
        overflow: 'hidden',
      }}>
        <Sidebar />
        <BirdsEyeView />
      </div>
    </AppContext.Provider>
  );
}

export default App;

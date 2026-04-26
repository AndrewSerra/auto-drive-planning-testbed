import { useEffect, useReducer, useRef, useState, createContext, useContext } from 'react';
import { positionReducer, type StateObject } from './reducers/positions';
import { WebsocketService } from './services/websocket';

const WS_URL = (import.meta as { env: Record<string, string> }).env.VITE_WS_URL ?? 'ws://localhost:8765';

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
            }} />
            <span style={{
              fontFamily: 'monospace',
              fontSize: '12px',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              flex: 1,
            }}>
              {id}
            </span>
            <span style={{ fontFamily: 'monospace', fontSize: '11px', color: '#9e9e9e', flexShrink: 0 }}>
              {Math.round(state.positions[id].angle)}°
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
        {/* Grid lines */}
        {state.grid && (() => {
          const { num_rows, num_cols } = state.grid;
          const xStep = (WORLD_MAX_X - WORLD_MIN_X) / num_cols;
          const yStep = (WORLD_MAX_Y - WORLD_MIN_Y) / num_rows;
          const lines = [];
          for (let c = 0; c <= num_cols; c++) {
            const x = WORLD_MIN_X + c * xStep;
            lines.push(<line key={`c${c}`} x1={x} y1={WORLD_MIN_Y} x2={x} y2={WORLD_MAX_Y} stroke="#222" strokeWidth="0.3" />);
          }
          for (let r = 0; r <= num_rows; r++) {
            const y = WORLD_MIN_Y + r * yStep;
            lines.push(<line key={`r${r}`} x1={WORLD_MIN_X} y1={y} x2={WORLD_MAX_X} y2={y} stroke="#222" strokeWidth="0.3" />);
          }
          return lines;
        })()}

        {/* Car circles + heading arrows (Y-flipped) */}
        <g transform={`scale(1,-1)`}>
          {Object.entries(positions).map(([id, { pos_x, pos_y, angle }]) => {
            const rad = angle * Math.PI / 180;
            const arrowLen = 3;
            const ax = pos_x + Math.cos(rad) * arrowLen;
            const ay = pos_y + Math.sin(rad) * arrowLen;
            const color = colorMap.get(id) ?? '#888';
            return (
              <g key={id}>
                <line x1={pos_x} y1={pos_y} x2={ax} y2={ay} stroke={color} strokeWidth="0.8" strokeLinecap="round" />
                <circle cx={pos_x} cy={pos_y} r={1.5} fill={color} />
              </g>
            );
          })}
        </g>

        {/* Car labels (unflipped) */}
        <g>
          {Object.entries(positions).map(([id, { pos_x, pos_y }]) => (
            <text
              key={id}
              x={pos_x + 2}
              y={-pos_y + 1}
              fontSize="3"
              fill={colorMap.get(id) ?? '#888'}
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
  const [state, dispatch] = useReducer(positionReducer, { system: 'RUNNING', positions: {}, grid: null });
  const [connStatus, setConnStatus] = useState<'CONNECTED' | 'DISCONNECTED'>('DISCONNECTED');
  const colorMapRef = useRef<Map<string, string>>(new Map());

  useEffect(() => {
    const ws = new WebsocketService(WS_URL);

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

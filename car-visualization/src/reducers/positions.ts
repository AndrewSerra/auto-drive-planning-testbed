
const Action = {
    NEW_POSITION: 'NEW_POSITION',
    SYSTEM_HALT: 'SYSTEM_HALT',
    SYSTEM_RESUME: 'SYSTEM_RESUME',
} as const;


export type PositionData = {
    car_id: string,
    pos_x: number,
    pos_y: number,
    grid_row: number,
    grid_col: number,
    angle: number,
}

type PositionState = {
    [car_id: string]: {
        pos_x: number,
        pos_y: number,
        grid_row: number,
        grid_col: number,
        angle: number,
    }
}

export type GridInfo = { num_rows: number; num_cols: number };
export type StateObject = { system: "HALT" | "RUNNING", positions: PositionState, grid: GridInfo | null };
export type ActionObject =
    | { type: typeof Action.NEW_POSITION, data: PositionData }
    | { type: typeof Action.SYSTEM_HALT }
    | { type: typeof Action.SYSTEM_RESUME }
    | { type: 'SET_GRID'; data: GridInfo };

function reducer(state: StateObject, action: ActionObject): StateObject {
    switch(action.type) {
        case Action.NEW_POSITION: {
            const { car_id, ...pos } = action.data;
            return { ...state, positions: { ...state.positions, [car_id]: pos } };
        }
        case Action.SYSTEM_HALT:
            return { ...state, system: "HALT" };
        case Action.SYSTEM_RESUME:
            return { ...state, system: "RUNNING" };
        case 'SET_GRID':
            return { ...state, grid: action.data };
        default:
            return state;
    }
}

function createPositionDataAction(data: PositionData): ActionObject {
    return {
        type: Action.NEW_POSITION,
        data: data,
    };
}

function createSystemHaltAction(): ActionObject {
    return {
        type: Action.SYSTEM_HALT
    };
}

function createSystemResumeAction(): ActionObject {
    return {
        type: Action.SYSTEM_RESUME
    };
}

export const positionReducer = reducer;
export const actionCreator = {
    createPositionDataAction,
    createSystemHaltAction,
    createSystemResumeAction,
};

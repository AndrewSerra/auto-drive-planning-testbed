
const Action = {
    NEW_POSITION: 'NEW_POSITION',
    SYSTEM_HALT: 'SYSTEM_HALT',
    SYSTEM_RESUME: 'SYSTEM_RESUME',
} as const;


export type PositionData = {
    carID: string,
    posX: number,
    posY: number,
    inbounds: boolean,
}

type PositionState = {
    [carID: string]: {
        posX: number,
        posY: number,
        inbounds: boolean,
    }
}

export type StateObject = { system: "HALT" | "RUNNING", positions: PositionState };
export type ActionObject =
    | { type: typeof Action.NEW_POSITION, data: PositionData }
    | { type: typeof Action.SYSTEM_HALT }
    | { type: typeof Action.SYSTEM_RESUME };

function reducer(state: StateObject, action: ActionObject): StateObject {
    switch(action.type) {
        case Action.NEW_POSITION: {
            const { carID, ...pos } = action.data;
            return { ...state, positions: { ...state.positions, [carID]: pos } };
        }
        case Action.SYSTEM_HALT:
            return { ...state, system: "HALT" };
        case Action.SYSTEM_RESUME:
            return { ...state, system: "RUNNING" };
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

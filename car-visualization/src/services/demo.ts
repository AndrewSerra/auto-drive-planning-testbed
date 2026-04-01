import type { ActionObject } from '../reducers/positions';

type ConnectionState = 'CONNECTED' | 'DISCONNECTED';

const CARS = [
  { carID: 'car-01', radius: 10, speed: 0.04, angleOffset: 0 },
  { carID: 'car-02', radius: 20, speed: 0.03, angleOffset: Math.PI / 2 },
  { carID: 'car-03', radius: 30, speed: 0.02, angleOffset: Math.PI },
  { carID: 'car-04', radius: 15, speed: 0.05, angleOffset: Math.PI * 1.5 },
  { carID: 'car-05', radius: 38, speed: 0.015, angleOffset: Math.PI / 4 },
];

export class DemoService {
  #dispatch: ((action: ActionObject) => void) | null = null;
  #connectionChangeHandler: ((state: ConnectionState) => void) | null = null;
  #intervalId: ReturnType<typeof setInterval> | null = null;
  #angles: number[];

  constructor() {
    this.#angles = CARS.map((c) => c.angleOffset);
    // Defer so that handlers can be assigned before firing
    setTimeout(() => {
      this.#connectionChangeHandler?.('CONNECTED');
      this.#start();
    }, 0);
  }

  public set dispatch(fn: ((action: ActionObject) => void) | null) {
    this.#dispatch = fn;
  }

  public set onconnectionchange(handler: ((state: ConnectionState) => void) | null) {
    this.#connectionChangeHandler = handler;
  }

  public close(): void {
    if (this.#intervalId !== null) {
      clearInterval(this.#intervalId);
      this.#intervalId = null;
    }
  }

  #start(): void {
    this.#intervalId = setInterval(() => {
      if (!this.#dispatch) return;
      CARS.forEach((car, i) => {
        this.#angles[i] += car.speed;
        this.#dispatch!({
          type: 'NEW_POSITION',
          data: {
            carID: car.carID,
            posX: parseFloat((car.radius * Math.cos(this.#angles[i])).toFixed(2)),
            posY: parseFloat((car.radius * Math.sin(this.#angles[i])).toFixed(2)),
            inbounds: true,
          },
        });
      });
    }, 100);
  }
}

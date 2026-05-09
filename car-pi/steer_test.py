import lgpio
import signal
import sys
import time

STEERING_PIN = 18
_PWM_FREQ    = 50     # Hz — standard servo frequency
_MIN_PW      = 1000   # µs — full left
_MAX_PW      = 2000   # µs — full right
_TRIM_STEP   = 10     # µs per calibration nudge

_PERIOD_US = 1_000_000 / _PWM_FREQ  # 20 000 µs

h = lgpio.gpiochip_open(0)
lgpio.gpio_claim_output(h, STEERING_PIN)


def _pw_to_duty(pw_us: int) -> float:
    return pw_us / _PERIOD_US * 100.0


def _set_pw(pw_us: int):
    lgpio.tx_pwm(h, STEERING_PIN, _PWM_FREQ, _pw_to_duty(pw_us))


def _value_to_pw(value: float, trim_us: int = 0) -> int:
    center = (_MIN_PW + _MAX_PW) // 2 + trim_us
    half_range = (_MAX_PW - _MIN_PW) // 2
    return max(_MIN_PW, min(_MAX_PW, round(center + value * half_range)))


def steer(value: float, trim_us: int = 0):
    pw = _value_to_pw(value, trim_us)
    _set_pw(pw)
    label = "LEFT" if value < -0.05 else "RIGHT" if value > 0.05 else "CENTER"
    print(f"  Steering {label} ({value:+.2f})  pw={pw} µs")


_trim_us = 0


def _shutdown(sig, frame):
    print("\nShutting down — centering servo.")
    _set_pw(_value_to_pw(0.0, _trim_us))
    time.sleep(0.3)
    lgpio.tx_pwm(h, STEERING_PIN, 0, 0)
    lgpio.gpiochip_close(h)
    sys.exit(0)


signal.signal(signal.SIGINT, _shutdown)
signal.signal(signal.SIGTERM, _shutdown)


def calibrate_center() -> int:
    """Interactively find servo mechanical center. Returns trim in µs."""
    trim = 0
    _set_pw(_value_to_pw(0.0, trim))
    print("=== Center calibration ===")
    print(f"  + = nudge right (+{_TRIM_STEP} µs)   - = nudge left (-{_TRIM_STEP} µs)   Enter = confirm")
    while True:
        try:
            key = input("cal> ").strip()
        except EOFError:
            break
        if key == "+":
            trim += _TRIM_STEP
        elif key == "-":
            trim -= _TRIM_STEP
        elif key == "":
            print(f"  Center confirmed. trim = {trim:+d} µs  (center at {(_MIN_PW + _MAX_PW) // 2 + trim} µs)")
            break
        else:
            print("  Use + / - to nudge, Enter to confirm.")
            continue
        _set_pw(_value_to_pw(0.0, trim))
        print(f"  trim: {trim:+d} µs  (center at {(_MIN_PW + _MAX_PW) // 2 + trim} µs)")
    return trim


STEPS = [
    ("Center",      0.0),
    ("Left full",  -1.0),
    ("Left half",  -0.5),
    ("Center",      0.0),
    ("Right half",  0.5),
    ("Right full",  1.0),
    ("Center",      0.0),
]

HOLD_SEC = 1.5

print("=== Steering test ===")
print(f"Pin: GPIO{STEERING_PIN}  pulse: {_MIN_PW}–{_MAX_PW} µs  freq: {_PWM_FREQ} Hz")
print()

_trim_us = calibrate_center()
print()

for label, value in STEPS:
    print(f"[{label}]")
    steer(value, _trim_us)
    time.sleep(HOLD_SEC)

print("\nCycle done. Entering interactive mode.")
print("  l = left full    r = right full    h = left half")
print("  k = right half   c = center        q = quit")

_set_pw(_value_to_pw(0.0, _trim_us))

while True:
    try:
        key = input("> ").strip().lower()
    except EOFError:
        break
    if key == "q":
        break
    elif key == "l":
        steer(-1.0, _trim_us)
    elif key == "h":
        steer(-0.5, _trim_us)
    elif key == "c":
        steer(0.0, _trim_us)
    elif key == "k":
        steer(0.5, _trim_us)
    elif key == "r":
        steer(1.0, _trim_us)
    else:
        print("  Unknown key. Use l/h/c/k/r/q.")

print(f"\nFinal trim: {_trim_us:+d} µs — hardcode into _MIN_PW/_MAX_PW offsets if satisfied.")
print("Centering and exiting.")
_set_pw(_value_to_pw(0.0, _trim_us))
time.sleep(0.3)
lgpio.tx_pwm(h, STEERING_PIN, 0, 0)
lgpio.gpiochip_close(h)

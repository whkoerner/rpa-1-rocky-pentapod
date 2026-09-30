# RPA-1 Build Guide — Computer-Only Simulation v0.1

**Status:** READY TO TEST  
**Milestone:** M0 — Repository and Communication  
**Hardware revision:** none; computer-only  
**Firmware/software revision:** Simulation v0.1  
**Last updated:** 2026-09-30

## 1. Goal

Run a deterministic 2D RPA-1 model before connecting physical motion hardware.
The build is meant to test five-limb state handling, joint-limit checks, contact
states, gait timing, actuator placeholders, safety stops, CSP-1 parsing, and
CSV logging.

It does not claim physical stability, torque, speed, walking performance, or
realistic contact physics.

## 2. Prerequisites

- A computer with Python 3.10 or newer.
- A local clone of this repository.
- No Arduino, Raspberry Pi, motors, sensors, or internet connection is required
  after Python packages are installed.

## 3. Parts

No robot parts are required.

## 4. Files

- `software/simulation/app.py` — Pygame window and keyboard controls.
- `software/simulation/model.py` — robot state, gait, contacts, actuators, and safety.
- `software/simulation/logger.py` — CSV logging.
- `software/simulation/config/robot.json` — simulation-only placeholder limits and timing.
- `software/simulation/tests/test_simulation.py` — automated tests.
- `software/csp/wire.py` — existing CSP-1 v0.1 decoder reused without modification.

## 5. Safety Before Power

There is no physical power stage in this build.

The main engineering risk is false confidence: a successful software run does
not prove that a physical RPA-1 will be stable, strong enough, or safe around
people. Keep all values in `robot.json` labeled as simulation placeholders
until hardware measurements replace them.

## 6. Wiring / Interfaces

There is no physical wiring.

Software interfaces:

```text
Keyboard -> simulator safety/gait controls -> SimActuator
CSP-1 line -> existing csp.wire decoder -> communication state only
Simulator state -> CSV logger -> software/simulation/logs/
```

CSP-1 v0.1 does not define motion intents. The simulator therefore does not
invent any.

## 7. Assembly

No physical assembly is required.

## 8. Software Setup

From the repository root:

### Windows PowerShell

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[simulation]"
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[simulation]"
```

## 9. Upload / Run

Nothing is uploaded to hardware.

Run:

```bash
python -m simulation.app
```

## 10. First Power-On

Expected safe startup behavior:

- the window opens with five visible limbs;
- robot mode is `IDLE`;
- simulated actuators are disabled;
- every contact begins as `UNKNOWN`;
- gait is stopped;
- no joint target changes automatically.

## 11. Test Procedure

First run the automated tests:

```bash
python -m unittest discover -s software/simulation/tests -v
```

Then perform this manual check:

1. Run `python -m simulation.app`.
2. Confirm five limbs are visible.
3. Press `1`, `2`, `3`, `4`, and `5` once so all contacts read `CONTACT`.
4. Press `A`; confirm mode becomes `ENABLED`.
5. Press `SPACE`; confirm one limb at a time enters the gait sequence.
6. Press `E` during the gait; confirm mode becomes `STOPPED` and gait stops.
7. Press `SPACE`; confirm gait does not restart while stopped.
8. Press `R`; confirm mode returns to `IDLE` and gait remains off.
9. Press `C`, type `C1|SOCIAL.HELLO|`, then press Enter. Confirm the existing
   CSP-1 intent is shown without causing motion.
10. Exit and confirm a CSV file was created under `software/simulation/logs/`.

## 12. Acceptance Criteria

Simulation v0.1 is ready to mark VERIFIED only after all of these are observed
and recorded:

- automated unit tests complete without failures;
- the display shows exactly five limbs with two simulated joints each;
- an out-of-range joint target causes a latched `STOPPED` state in the test suite;
- gait cannot start unless all five contact states are `CONTACT`;
- loss of a required support contact stops the gait in the test suite;
- E-stop disables all simulated actuators and requires explicit reset;
- reset returns to `IDLE` and does not automatically resume gait;
- a valid existing CSP-1 message is accepted without moving the robot;
- an invalid/unknown CSP-1 message fails closed;
- a CSV log is produced for a simulator run;
- repeating the automated fixed-step sequence produces the same state snapshot.

Do not mark this build VERIFIED until a dated test result is saved.

## 13. Troubleshooting

If Python cannot find `simulation` or `csp`, activate the virtual
environment and rerun:

```bash
python -m pip install -e ".[simulation]"
```

If the gait immediately stops, reset, cycle all five contacts to `CONTACT`,
arm again, then start the gait.

If Pygame cannot open a window, confirm the optional simulation dependency was
installed in the active environment.

## 14. Shutdown

Press `ESC` or close the window. No physical disconnect is needed.

## 15. Evidence to Save

Save:

- terminal output from the unit-test command;
- one generated CSV run log;
- the commit SHA tested;
- a short note listing any failed acceptance criterion.

Do not commit routine generated CSV logs unless one is intentionally selected
as formal test evidence.

## 16. Next Step

After Simulation v0.1 passes, add a small replay tool that feeds a saved,
timestamped command sequence into the same model and compares the resulting log.
Do not add ROS 2, 3D physics, AI, or Raspberry Pi hardware control yet.

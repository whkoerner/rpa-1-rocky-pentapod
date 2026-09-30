# RPA-1 Computer-Only Simulation v0.1

**Status:** READY TO TEST

This package is a low-setup software-in-the-loop simulator for RPA-1 before physical motion hardware is connected.

It intentionally tests control structure rather than realistic physics.

## What it includes

- 2D body with five visible limbs
- two placeholder joints per limb
- configurable joint limits
- contact states: `UNKNOWN`, `CONTACT`, and `FREE`
- fixed-step gait timing
- simulated actuator interface
- latched E-stop and explicit reset
- existing CSP-1 v0.1 message validation
- CSV state logs
- `unittest` regression tests

## Important assumption

The geometry, angles, gait timing, and simulated actuator rate in
`config/robot.json` are software-only placeholders. They are not measured
RPA-1 hardware values and must not be reported as physical performance.

CSP-1 v0.1 currently defines communication intents only. This simulator does
not invent motion intents. Valid CSP-1 messages can be entered and logged, but
they do not start a gait or command a joint.

## Install

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

## Run

```bash
python -m simulation.app
```

Controls:

- `A`: arm simulated actuators
- `1` through `5`: cycle that limb through `UNKNOWN -> CONTACT -> FREE`
- `SPACE`: start or stop the simple gait
- `E`: emergency stop
- `R`: reset to IDLE; does not restart motion
- `C`: enter one CSP-1 wire line, for example `C1|SOCIAL.HELLO|`
- `ESC`: cancel CSP entry or quit

To start the gait safely in v0.1, set all five contacts to `CONTACT`, press
`A`, then press `SPACE`.

## Logs

Generated CSV files are written to:

```text
software/simulation/logs/
```

CSV logs are ignored by Git so test output is not committed accidentally.

## Tests

From the repository root:

```bash
python -m unittest discover -s software/simulation/tests -v
```

See `docs/build-guides/simulation-v0.1-build.md` for the acceptance procedure.

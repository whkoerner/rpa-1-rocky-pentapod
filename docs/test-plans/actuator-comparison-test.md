# TP-ACT-001 — Guarded Artificial-Muscle Comparison

**Purpose:** Select an actuation direction using comparable evidence rather than appearance or popularity.

**Status:** Draft; mentor/makerspace review required before pressure testing.

## Specimens

1. **Electric tendon:** low-voltage motor or servo, capstan, cable, known series spring, position feedback, and current measurement.
2. **Pneumatic:** rated small artificial muscle or a deliberately low-pressure research specimen with regulator, relief, pressure sensor, minimal air volume, guard, and remote valve/manual inlet. No homemade reservoir.
3. **Hydraulic demonstration:** paired commercial syringes with water, flexible tubing, containment tray, and manual input only. No motorized pump or stored high pressure.

All specimens drive the same hinge, output lever arm, angle range, and load attachment.

## Required equipment

- rigid bolted test stand and transparent/polycarbonate guard;
- physical actuator-energy stop for the electric specimen;
- regulated current-limited low-voltage supply;
- digital scale or appropriate load cell;
- joint encoder or measured angle scale;
- current sensor and multimeter;
- pressure sensor/gauge for pneumatic tests;
- thermometer or temperature sensor;
- phone/video only outside the exclusion zone;
- sound-level instrument if available;
- safety glasses and spill tray.

## Prohibited configurations

- PVC or improvised pressure tanks;
- compressed gas bottles without qualified supervision and rated regulation;
- superheated water, steam, mercury, or oil injection tests;
- hands inside the motion or burst envelope while energized;
- blocked relief path;
- unattended cycling.

## Common geometry

Document before testing:

- hinge-to-actuator moment arm;
- hinge-to-load moment arm;
- unloaded and loaded angle range;
- specimen mass including the hardware uniquely required by it;
- supply, valve/driver, sensor, and control revision;
- guard and E-stop arrangement.

## Procedure

### 1. Inspection and zeroing

1. Inspect fasteners, cable routing, hoses, fittings, guards, wiring, and relief path.
2. Confirm no person is inside the exclusion zone.
3. Exercise the E-stop or isolation control before adding load.
4. Zero force, angle, current, and pressure measurements.
5. Record ambient temperature and background sound.

### 2. No-load travel

- Command or manually apply 10%, 25%, 50%, 75%, and 100% of the released input range.
- Record input, angle/displacement, settling time, overshoot, and return error.
- Repeat three times.

### 3. Force-displacement curve

- Use at least five load points within the stand and specimen ratings.
- Approach each point from both directions.
- Record input, force, displacement, current/pressure, and temperature.
- Never exceed the lowest-rated component or stand limit.

### 4. Hysteresis and repeatability

- Run 10 slow loading/unloading cycles over the released range.
- Plot output against input in both directions.
- Report maximum hysteresis width and standard deviation at each point.

### 5. Step response

- Apply three bounded step commands or manual input changes.
- Report 10–90% rise time, overshoot, and time to remain inside a defined settling band.
- Pneumatic and hydraulic specimens remain below the reviewed pressure limit.

### 6. Duty and thermal behavior

- Cycle the electric specimen for 10 minutes at its proposed duty cycle.
- Stop if current, driver, motor, cable, spring, or structure exceeds its documented limit.
- Pressure specimens receive only the reviewed cycle count and must be inspected between sets.

### 7. Failure behavior

Test only failures that the rig safely contains:

- stale or disconnected electric command;
- encoder disconnect;
- current-limit event;
- introduced tendon slack with no load or restrained load;
- pneumatic supply removal and controlled vent;
- minor syringe-line air bubble or controlled low-pressure disconnect inside tray.

Do not intentionally burst a component.

## Data columns

```text
test_id,timestamp,specimen,revision,input_type,input_value,
joint_angle_deg,output_force_n,current_a,voltage_v,pressure_kpa,
temperature_c,rise_time_ms,settling_time_ms,sound_dba,
system_mass_g,observed_fault,operator_notes
```

## Selection criteria

Score each complete system—not just its actuator—using the project weights:

- cost 25%;
- safety 20%;
- controllability/debugging 20%;
- mobile mass/packaging 15%;
- biological/visual fidelity 10%;
- portable-energy efficiency 10%.

## Pass criteria

- No guard breach, uncontrolled motion, leak outside containment, or overheated component.
- Complete common dataset for all three specimens.
- At least 10 valid hysteresis cycles per specimen.
- Costs and masses include required support hardware.
- Decision record identifies uncertainty and the next falsifying experiment.

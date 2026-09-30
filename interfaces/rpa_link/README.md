# RPA-Link v0.1

Status: READY TO TEST

RPA-Link is the hardware-independent command and telemetry boundary for the RPA-1 simulator, a Linux computer, a Raspberry Pi, and later real-time microcontrollers.

It defines message meaning separately from transport. The simulator should send the same logical command whether the other end is fake hardware, a Raspberry Pi bridge, or a microcontroller.

## Scope

Included in v0.1:

- deterministic command and telemetry envelopes
- monotonic timestamps
- explicit integer units
- heartbeat and timeout rules
- latched software E-stop behavior
- fake-hardware mode
- JSON over local UDP for simulator/Linux/Pi use
- a documented binary serial frame for later microcontroller adapters

Not included:

- ROS 2
- motor, servo, pneumatic, or hydraulic drivers
- measured physical joint limits
- physical E-stop wiring
- realistic physics
- automatic network discovery

## Assumptions

The final RPA-1 joint layout, actuator type, physical safe-stop behavior, and measured limits are not fixed yet. This interface therefore uses numbered joint IDs and does not invent physical values.

The 100 ms heartbeat period, 500 ms heartbeat timeout, and 250 ms command timeout below are initial software design values. They are not measured hardware requirements.

## Logical path

    Simulator or behavior code
            |
            | RPA-Link JSON
            v
    Linux PC or Raspberry Pi
            |
            | RPA-Link binary adapter later
            v
    Real-time microcontroller
            |
            v
    Actuator-specific driver

CSP-1 / Chordic stays above this layer. A semantic intent may choose a behavior, but the real-time controller receives low-level RPA-Link motion commands rather than language messages.

## Node IDs

Recommended starting IDs:

- 0: broadcast
- 1: supervisor
- 2: simulator
- 3: Raspberry Pi bridge
- 16: motion controller

The IDs are protocol configuration, not physical addresses.

## Units

Use integer SI-derived units on the wire:

| Quantity | Field suffix | Unit |
|---|---|---|
| angle | _urad | microradians |
| angular velocity | _urad_s | microradians/second |
| distance | _um | micrometers |
| linear velocity | _um_s | micrometers/second |
| force | _mN | millinewtons |
| torque | _mNm | millinewton-meters |
| voltage | _mV | millivolts |
| current | _mA | milliamps |
| temperature | _mC | millidegrees Celsius |
| time | _us | microseconds |

Do not put an unlabeled value such as angle=45 on the wire.

## Common JSON envelope

Every JSON message contains:

    {
      "protocol": "RPA-LINK",
      "version": 1,
      "type": "HEARTBEAT",
      "source": 1,
      "destination": 16,
      "sequence": 42,
      "timestamp_us": 91822000,
      "ttl_ms": 500,
      "payload": {}
    }

Required fields:

- protocol: must be RPA-LINK
- version: currently 1
- type: message type
- source: sender node ID, 0 through 255
- destination: receiver node ID, 0 through 255; 0 is broadcast
- sequence: unsigned 32-bit sender sequence number
- timestamp_us: sender monotonic microseconds
- ttl_ms: maximum useful queue age for this message
- payload: message-specific object

The JSON schema is in rpa_link.schema.json.

## Timestamps

Control time uses a monotonic clock, not wall-clock time.

On Python hosts use time.monotonic_ns() converted to microseconds.

A sender timestamp is useful for logging and ordering. Safety timeouts do not assume clocks on two machines are synchronized. A receiver measures time since the most recent valid packet was received using its own monotonic clock.

Wall-clock UTC may be added to logs, but must not control motion timeouts.

## Message types

HELLO
: Announces a node and role when it starts.

HEARTBEAT
: Proves the supervisor link is alive.

SET_MODE
: Requests DISABLED, READY, ACTIVE, or SAFE_STOP. ESTOP is entered by the E-stop path, not by normal arming.

JOINT_POSITION_CMD
: Commands numbered joints in microradians with an optional maximum angular velocity.

ESTOP
: Immediately latches software E-stop.

ESTOP_RESET_REQUEST
: Requests clearing software E-stop only after communications are healthy and local safety conditions permit it.

JOINT_TELEMETRY
: Reports joint state. Missing sensors must use a validity flag instead of invented measurements.

SYSTEM_TELEMETRY
: Reports controller mode, E-stop state, link state, and faults.

FAULT
: Reports a defined fault code.

ACK
: Acknowledges commands that require an explicit response.

## Modes

DISABLED
: Communications may run, but motion is not accepted.

READY
: Communications are healthy and the controller is prepared, but motion commands are still not accepted.

ACTIVE
: Valid motion commands may reach the actuator abstraction.

SAFE_STOP
: A communication or command watchdog failed. New motion commands are blocked.

ESTOP
: Emergency stop is latched. New motion commands are blocked until an explicit reset procedure succeeds.

Startup must always begin DISABLED.

## Heartbeat and watchdogs

Starting design values:

- heartbeat transmit period: 100 ms
- heartbeat timeout: 500 ms
- command timeout while ACTIVE: 250 ms

If the motion controller is ACTIVE and a valid heartbeat is not received before the heartbeat timeout, it enters SAFE_STOP locally.

If the motion controller is ACTIVE and no valid motion command is received before the command timeout, it enters SAFE_STOP locally.

Linux, the simulator, and the Raspberry Pi must not be the only places that enforce these watchdogs. The real-time controller must eventually enforce them itself.

## Message TTL

A message that has spent longer than ttl_ms waiting in a local receive queue is stale and must be discarded.

Do not compare unsynchronized sender and receiver monotonic clocks to decide whether a packet is stale.

## Joint command

Example:

    {
      "protocol": "RPA-LINK",
      "version": 1,
      "type": "JOINT_POSITION_CMD",
      "source": 1,
      "destination": 16,
      "sequence": 85,
      "timestamp_us": 51240000,
      "ttl_ms": 250,
      "payload": {
        "joints": [
          {
            "joint_id": 0,
            "target_urad": 500000,
            "max_velocity_urad_s": 300000
          }
        ]
      }
    }

The host must not send raw PWM, duty cycle, or actuator-specific values through this interface. Hardware conversion belongs in the actuator driver.

The real controller must later enforce measured joint and actuator limits even if the host software already checked them.

## Telemetry validity

If a physical measurement does not exist, report that explicitly.

Example:

    {
      "joint_id": 0,
      "commanded_urad": 500000,
      "position_valid": false
    }

Do not copy the command into a fake position field and present it as a measurement.

Contact state should distinguish UNKNOWN, NO_CONTACT, and CONTACT so "no sensor" is not confused with "sensor says no contact."

## Software E-stop

Receiving ESTOP causes:

    estop_latched = true
    mode = ESTOP

Software E-stop remains latched across supervisor reconnects. A supervisor restart must not automatically resume motion.

ESTOP_RESET_REQUEST may only succeed when:

- communications are healthy
- the controller is not ACTIVE
- pending motion commands are cleared
- the physical E-stop is released once one exists

For the fake controller, the physical E-stop input is represented by a boolean test hook.

A future physical E-stop must inhibit hazardous actuator motion independently of Linux, Raspberry Pi, network software, or this Python package.

## SAFE_STOP

The logical protocol defines SAFE_STOP as "stop accepting new motion commands."

The final physical reaction cannot be chosen yet because the actuator and mechanism are not fixed. Later hardware configuration must explicitly choose a safe policy such as controlled stop, hold, or disable output. Do not assume that simply removing power is safe because a limb could fall.

## Local/offline transport

Simulator, Linux, and Raspberry Pi use one complete JSON message per UDP datagram.

Default loopback ports:

- command input: 127.0.0.1:7401
- telemetry output: 127.0.0.1:7402

Loopback is the default so the first test never leaves the computer. A Raspberry Pi can later use a private LAN address without changing message meaning.

Invalid JSON, unsupported versions, unknown message types, and malformed payloads are rejected.

## Microcontroller transport

Do not require a small real-time microcontroller to parse JSON.

A later serial adapter should preserve the same logical fields in this binary envelope:

    version       u8
    type          u8
    source        u8
    destination   u8
    sequence      u32
    timestamp_us  u64
    ttl_ms        u16
    payload_len   u16
    payload       bytes
    crc16         u16

Use little-endian integers.

Frame each binary packet with COBS plus a 0x00 terminator. CRC16 detects corrupted frames.

The first physical connection should prefer USB serial or UART for beginner-friendly debugging. CAN or ROS 2 can be added later without changing the logical RPA-Link messages.

The binary serial adapter is documented here but intentionally not implemented until a specific real-time controller is selected.

## Fake-hardware mode

The fake controller is in:

    software/rpa_link/fake_hardware.py

It implements the watchdog and E-stop state machine but does not invent physical motion.

When a joint command is accepted, fake telemetry reports the command and sets position_valid to false.

Run from the repository root after an editable install:

    python -m rpa_link.fake_hardware

Defaults:

- listens for commands on 127.0.0.1:7401
- sends telemetry to 127.0.0.1:7402

Useful fault injection:

    python -m rpa_link.fake_hardware --estop
    python -m rpa_link.fake_hardware --drop-heartbeat

## Acceptance tests

Install the repository in editable mode:

    python -m pip install -e .

Run the RPA-Link tests:

    python -m unittest discover -s software/rpa_link/tests -v

Acceptance criteria:

- message JSON round-trips without changing integer fields
- unsupported protocol versions fail closed
- startup mode is DISABLED
- ACTIVE requires a recent heartbeat
- heartbeat timeout changes ACTIVE to SAFE_STOP
- command timeout changes ACTIVE to SAFE_STOP
- a stale queued motion command is rejected
- ESTOP is latched and blocks motion
- E-stop reset returns to DISABLED and never ACTIVE
- fake telemetry never claims a physical position measurement
- no physical hardware is required for the tests

Do not mark RPA-Link VERIFIED until the test command has actually been run and the result is saved.

## Safety risks

- Communication loss: local watchdog must stop accepting motion.
- Old commands: TTL and command watchdog prevent delayed motion from being treated as current.
- Corrupted data: validation is required before a command reaches the actuator layer; the later binary adapter also needs CRC.
- Unexpected restart: startup is always DISABLED.
- Joint overtravel: final real-time firmware must independently enforce measured limits.
- False telemetry: unsupported sensors use validity flags.
- E-stop dependence on software: final hardware needs an independent physical E-stop path.
- Limb collapse after power removal: physical SAFE_STOP behavior must be chosen only after actuator and mechanism testing.

## Next step

Keep the next change small: connect the existing computer-only simulator to the local UDP adapter and fake controller. Do not add Raspberry Pi GPIO, motors, ROS 2, or real actuator drivers yet.

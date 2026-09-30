# Rocky Brain v0.1 firmware

Open `rocky_brain_v0_1.ino` in Arduino IDE 2, select **Arduino Uno**, select the board's USB port, and click **Upload**.

The sketch uses only Arduino's built-in functions. It does not require a library installation.

## Physical controls

- D2 button: switch between Chordic-only and translated-English mode.
- D4 button: play the selected phrase, then select the next phrase.
- Built-in LED off: Chordic-only mode.
- Built-in LED on: translated-English mode.

English speech is produced by the companion browser app, not by the passive buzzer. The buzzer always plays the original Chordic phrase.

## Serial commands

At 115200 baud, send newline-terminated commands:

```text
HELP
LIST
STATUS
MODE MUSICAL
MODE TRANSLATED
MODE TOGGLE
PLAY HELLO
PLAY YES
PLAY NO
PLAY THANK_YOU
PLAY AMAZE
PLAY PLEASE_REPEAT
PLAY NOT_UNDERSTOOD
PLAY STOP
STOP
```

Every response begins with `EVENT|`, making it straightforward for later Raspberry Pi, ESP32, ROS 2, or AI software to use the same interface.

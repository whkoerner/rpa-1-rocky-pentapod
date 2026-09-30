# Rocky Brain v0.1 firmware

This is the smallest bench-testable RPA-1 brain.

**Hardware:** Elegoo/Arduino Uno R3, two momentary buttons, one passive buzzer, USB-connected computer.

**Not included yet:** motors, internet, AI, Raspberry Pi, microphone, speech recognition, batteries, or autonomous behavior.

Open `rocky_brain_v0_1.ino` in Arduino IDE 2, select **Arduino Uno**, select the board's USB port, click **Verify**, then click **Upload**.

No external Arduino libraries are required.

## Pins

| Uno pin | Connection |
|---|---|
| D2 | MODE button to GND |
| D3 | SPEAK button to GND |
| D9 | passive buzzer through 220-ohm resistor |
| GND | button and buzzer return |

The buttons use `INPUT_PULLUP`, so do not add a 5 V wire to either button.

## Modes

- **Communication:** the buzzer plays Chordic and Serial Monitor prints only the CSP-1 token.
- **Translation:** the same Chordic tones play, and Serial Monitor also prints the fixed English meaning.
- Press the D2 button to switch modes.
- Press the D3 button to play the next phrase.

The six starter phrases are existing CSP-1 concepts: `SOCIAL.hello`, `SOCIAL.yes`, `SOCIAL.no`, `ACTION.help`, `SOCIAL.thank_you`, and `SOCIAL.goodbye`.

## Serial Monitor

Use **9600 baud** and **Newline**.

Commands:

```text
HELP
STATUS
LIST
NEXT
MODE COMM
MODE TRANSLATE
SAY HELLO
SAY YES
SAY NO
SAY HELP
SAY THANK_YOU
SAY GOODBYE
```

## Quick pre-commit hardware test

1. Upload the sketch.
2. Open Serial Monitor at 9600 baud.
3. Send `STATUS`; it should report `MODE: COMMUNICATION`.
4. Send `SAY HELLO`; the buzzer should play five notes and Serial Monitor should print `CSP-1: SOCIAL.hello`.
5. Send `MODE TRANSLATE`, then `SAY HELLO`; it should additionally print `ENGLISH: Hello`.
6. Press D2 once; the displayed mode should switch.
7. Press D3 repeatedly; the six phrases should cycle and return to HELLO.

Do not record these as demonstrated results until you have actually run the test.

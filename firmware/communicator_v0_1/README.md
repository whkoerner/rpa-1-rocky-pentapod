# Arduino Communicator v0.1

## Purpose

The first low-risk hardware result: two buttons, a passive piezo, and an RGB LED play four versioned CSP-1 musical tokens and toggle translation mode without blocking the main loop.

## Parts

- Arduino Uno/Nano-compatible 5 V board
- passive piezo element; an active buzzer cannot reproduce defined pitches
- common-cathode RGB LED
- three 220–330 Ω LED resistors
- optional 100 Ω series resistor for a small passive piezo
- two momentary pushbuttons
- breadboard and jumpers

## Wiring

| Part | Arduino pin | Other connection |
|---|---:|---|
| Translation button | D2 | other side to GND |
| Phrase button | D4 | other side to GND |
| RGB red through resistor | D5 | common cathode to GND |
| RGB green through resistor | D6 | common cathode to GND |
| RGB blue through resistor | D10 | common cathode to GND |
| Passive piezo | D9 | other side to GND; use only a small piezo load |

The code uses `INPUT_PULLUP`, so a pressed button reads LOW. Never connect an 8 Ω speaker directly to an Arduino pin; use an appropriate amplifier/transistor stage designed for it.

## Expected behavior

- Blue LED: translation mode off.
- Green LED: translation mode on.
- Violet LED: phrase playing.
- Translation button: toggles the mode and plays a short confirmation motif.
- Phrase button: cycles through `SOCIAL.hello`, `SOCIAL.yes`, `GRAM.yes_no_question`, and `SAFETY.warning`.
- Serial monitor at 115200 baud shows each state and phrase.

## Acceptance test

1. Inspect power and polarity with USB disconnected.
2. Power from USB only.
3. Confirm safe, quiet volume at 1 m; move the piezo farther away if uncomfortable.
4. Press the translation button 100 times at varied intervals. Pass with at least 99 correct single toggles and no stuck state.
5. Press the phrase button through 10 complete cycles. Confirm order and pitches against the CSP specification.
6. Press buttons while a phrase plays. Confirm the controller remains responsive and never locks up.
7. Cycle power 20 times. Confirm no sound until a deliberate button press.

Record board model, component values, code commit, failures, and test results.

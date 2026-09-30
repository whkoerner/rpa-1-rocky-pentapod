# Build guide: Rocky Brain v0.1

**Status:** READY TO TEST  
**Milestone:** M0 — Repository and Communication  
**Release:** Pre-release  
**Last updated:** 2026-09-30

## Goal

Build the first RPA-1 brain with only:

- Elegoo Super Starter Kit Uno R3
- two momentary pushbuttons
- passive buzzer
- breadboard and jumper wires
- one 220-ohm resistor
- USB-connected computer

This build has no motors, internet, AI, Raspberry Pi, microphone, battery pack, or autonomous behavior.

The communication language is **Chordic**. Its machine encoding is **CSP-1**. This is an original project protocol, not a claim about a movie language.

## What the controls do

- **MODE button (D2):** switches between Communication and Translation mode.
- **SPEAK button (D3):** plays the next stored Chordic message.
- **Passive buzzer (D9):** plays the CSP-1 notes.
- **USB Serial Monitor:** shows the CSP-1 token and, only in Translation mode, its fixed English meaning.

Translation mode does not use AI. It is a small lookup table stored in the Arduino sketch.

## Parts

| Qty | Part |
|---:|---|
| 1 | Elegoo/Arduino Uno R3 |
| 1 | USB data cable |
| 1 | breadboard |
| 2 | momentary pushbuttons |
| 1 | passive buzzer |
| 1 | 220-ohm resistor |
| several | jumper wires |

**Assumption:** you are using the passive buzzer from the Elegoo kit. If you are unsure which buzzer is passive, identify it before powering the circuit.

## Wiring

Disconnect USB before changing wires.

| Component | Uno connection |
|---|---|
| MODE button side A | D2 |
| MODE button side B | GND |
| SPEAK button side A | D3 |
| SPEAK button side B | GND |
| passive buzzer + | D9 through 220-ohm resistor |
| passive buzzer - | GND |

Both buttons use the Uno's internal pull-up resistors. Do not connect either button to 5 V.

### Pushbutton orientation

Place each four-leg tactile switch across the breadboard center trench. The two legs on one side are normally already connected. D2/D3 and GND must connect to opposite electrical sides.

```text
MODE:   D2 ---- button ---- GND
SPEAK:  D3 ---- button ---- GND
BUZZER: D9 ---- 220 ohm ---- (+ buzzer -) ---- GND
```

## Arduino IDE setup

1. Install Arduino IDE 2.
2. Connect the Uno with the USB data cable.
3. Open `firmware/rocky_brain_v0_1/rocky_brain_v0_1.ino`.
4. Select **Tools -> Board -> Arduino AVR Boards -> Arduino Uno**.
5. Select **Tools -> Port -> [your Uno port]**.
6. Click **Verify**.
7. Click **Upload**.
8. Open **Tools -> Serial Monitor**.
9. Set **9600 baud** and **Newline**.

The exact COM number varies by computer.

## Serial commands

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

## Starter vocabulary

These are already-defined CSP-1 concepts from `language/specification/csp_v0_1.yaml`.

| Command name | CSP-1 token | English translation |
|---|---|---|
| HELLO | SOCIAL.hello | Hello |
| YES | SOCIAL.yes | Yes |
| NO | SOCIAL.no | No |
| HELP | ACTION.help | Help |
| THANK_YOU | SOCIAL.thank_you | Thank you |
| GOODBYE | SOCIAL.goodbye | Goodbye |

The firmware derives its note patterns from the CSP-1 class/code encoding already documented in the repository. Arduino `tone()` uses rounded integer frequencies.

## Test in stages

### Test 1 — Uno and Serial only

Leave the breadboard disconnected.

Upload the firmware and send:

```text
STATUS
```

**Pass:** Serial Monitor reports `RPA-1 ROCKY BRAIN v0.1` and `MODE: COMMUNICATION`.

### Test 2 — passive buzzer

Connect only the buzzer circuit and send:

```text
SAY HELLO
```

**Pass:** Serial Monitor prints `CSP-1: SOCIAL.hello` and the passive buzzer produces a five-note sequence.

### Test 3 — MODE button

Connect the D2 button and press it once.

**Pass:** the mode changes to `TRANSLATION`. Press it again and it returns to `COMMUNICATION`.

### Test 4 — SPEAK button

Connect the D3 button and press it repeatedly.

**Pass:** messages cycle in this order:

```text
HELLO -> YES -> NO -> HELP -> THANK_YOU -> GOODBYE -> HELLO
```

### Test 5 — translation behavior

Send:

```text
MODE TRANSLATE
SAY HELLO
```

**Pass:** Serial Monitor includes:

```text
CSP-1: SOCIAL.hello
ENGLISH: Hello
```

Then send:

```text
MODE COMM
SAY HELLO
```

**Pass:** `CSP-1: SOCIAL.hello` appears, but no `ENGLISH:` line is printed.

## Acceptance criteria

Do not mark these complete until you personally observe them.

```text
[ ] Sketch verifies in Arduino IDE
[ ] Sketch uploads to Uno
[ ] Serial Monitor works at 9600 baud
[ ] HELP, STATUS, LIST, and NEXT work
[ ] All six stored messages produce tone sequences
[ ] D2 switches modes once per deliberate press
[ ] D3 cycles through all six messages
[ ] Communication mode omits the English line
[ ] Translation mode prints the fixed English line
[ ] Pressing either button does not reset the Uno
[ ] No component or wire becomes hot
```

## Safety

- Disconnect USB before rewiring.
- Never intentionally connect an Uno output pin directly to GND.
- Use the 220-ohm series resistor with the passive buzzer.
- Do not use the kit's 8-ohm speaker directly from an Uno GPIO.
- Do not add motors, external batteries, or the breadboard power module to this test.
- Keep the buzzer away from your ear.

## Troubleshooting

**No port appears:** unplug the Uno, note the ports, reconnect it, and choose the new port. Try another USB data cable if needed.

**Upload fails:** confirm **Arduino Uno** and the correct port are selected. Close other programs using the port.

**Unreadable Serial Monitor:** set it to **9600 baud**.

**Commands do nothing:** set the line ending to **Newline**, then send `HELP`.

**Button always reads pressed:** rotate the four-leg button 90 degrees or move the wires to opposite electrical sides.

**One press appears to trigger more than once:** first check loose wires and button orientation. The firmware includes basic debounce protection.

**Buzzer only clicks or gives one fixed buzz:** confirm that you used the passive buzzer rather than the active buzzer.

**Uno resets when a button is pressed:** disconnect USB immediately and inspect the wiring. The button must connect D2 or D3 to GND; it must not short 5 V to GND.

## Pre-commit test

After making or downloading this change, run the existing software tests from the repository root:

```bash
python -m pip install -e .
python -m unittest discover -s language/tests -v
```

Then, with the Uno connected, use Arduino IDE **Verify** on:

```text
firmware/rocky_brain_v0_1/rocky_brain_v0_1.ino
```

The Python tests check that the existing CSP-1 software still behaves consistently. Arduino IDE Verify checks the actual Uno sketch. Hardware acceptance still requires the staged tests above.

## Short next step

Build only the Uno + passive buzzer first. Verify `SAY HELLO` through `SAY GOODBYE`. Then add D2 and test it. Add D3 last.

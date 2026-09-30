# Build guide: Rocky Brain v0.1

## What counts as the brain

Rocky Brain v0.1 has two cooperating layers:

1. **Elegoo Uno R3 — reflex and musical controller.** It reads physical buttons, stores eight deterministic Chordic utterances, drives the passive buzzer, starts silently, and continues working if the computer app closes.
2. **Computer — English translation layer.** A local browser page receives the exact phrase identity over USB and optionally speaks its English meaning. The computer does not invent a translation from arbitrary notes.

The Uno cannot run useful speech recognition, long-term memory, or conversational AI. Those belong on a later Raspberry Pi or other Linux computer. The serial protocol introduced here is designed to survive that upgrade.

## Language name

The language is **Chordic**. Its versioned machine encoding is the **Chordic Semantic Protocol (`CSP-1`)**.

## Parts from the Elegoo Super Starter Kit

- Elegoo Uno R3 and USB cable
- breadboard
- two momentary pushbuttons
- passive buzzer, not the active buzzer
- one 220-ohm resistor for the buzzer
- jumper wires

The official Super Starter Kit is compatible with the Uno/Arduino IDE platform and includes guided component projects. Use Elegoo's kit tutorial to identify unfamiliar components.

## Wiring with USB disconnected

The firmware uses the Uno's internal button pull-up resistors, so the buttons connect pins to ground when pressed.

| Component node | Connect to |
|---|---|
| Mode button terminal 1 | Uno D2 |
| Mode button terminal 2 | Uno GND |
| Phrase button terminal 1 | Uno D4 |
| Phrase button terminal 2 | Uno GND |
| Passive buzzer `+` | Uno D9 through 220-ohm resistor |
| Passive buzzer `-` | Uno GND |

Place each pushbutton across the breadboard's center trench. On a four-leg tactile switch, the two legs on one side are normally already connected. D2/D4 and GND must go to opposite sides that connect only while the button is pressed.

Do not connect the kit's 8-ohm speaker directly to an Uno pin. Do not use the breadboard power-supply module or 9 V battery for this prototype; power the circuit from USB only.

## Upload firmware

1. Install **Arduino IDE 2** from Arduino's official site.
2. Connect the Uno to the computer with USB.
3. Open `firmware/rocky_brain_v0_1/rocky_brain_v0_1.ino`.
4. Choose **Tools → Board → Arduino AVR Boards → Arduino Uno**.
5. Choose **Tools → Port** and select the Uno.
6. Click **Verify**. It must finish without an error.
7. Click **Upload**. Wait for `Done uploading`.
8. Open Serial Monitor, set **115200 baud**, and choose a newline line ending.
9. Send `STATUS`. Expect a line beginning `EVENT|STATUS|MODE=MUSICAL`.
10. Close Serial Monitor before opening the browser console.

## Run the English translation console

1. Open `software/brain_web/index.html` in desktop Chrome or Edge.
2. Click **Connect to Uno** and select the same serial port used by Arduino IDE.
3. Press the physical D2 button or the webpage mode button. The Uno's built-in LED should turn on and the page should show **Translated English**.
4. Press the physical D4 button. Rocky plays Chordic through the buzzer; the computer displays the CSP tokens and speaks the exact English phrase.
5. Press D2 again. The built-in LED turns off. Rocky continues making Chordic sounds, but the computer no longer speaks English.

If the page cannot use Web Serial, run `py -m http.server 8000` on Windows or `python3 -m http.server 8000` on macOS/Linux from the `software/brain_web` folder, then open `http://localhost:8000` in Chrome or Edge.

## Expected behavior

- Safe startup: no tone, no movement, translation off.
- Built-in LED off: Chordic-only mode.
- Built-in LED on: Chordic plus English translation.
- D4 cycles through hello, yes, no, thank you, amaze, please repeat, not understood, and warning/stop.
- Browser phrase buttons play a chosen utterance directly.
- Unrecognized serial commands return an explicit error rather than being guessed.

## Common mistakes

- **One long unchanging buzz:** the active buzzer was used; switch to the passive buzzer.
- **Button fires constantly:** D2/D4 and GND are connected to legs that are already common; rotate the button 90 degrees.
- **Upload port is missing:** try a data-capable USB cable and check the selected board and port.
- **Browser cannot connect:** close Serial Monitor; only one application can use the port.
- **No English voice:** enable **Speak English**, set translated mode, and verify that the operating system has a speech voice installed.
- **Sound is unpleasant:** disconnect USB, confirm the 220-ohm series resistor, cover the buzzer opening lightly, and never hold it near an ear.

## Demonstration video

Record one continuous shot showing startup, both physical buttons, all eight phrases, translation on/off, the visible token display, and recovery after unplugging/reconnecting USB. Keep the wiring visible.

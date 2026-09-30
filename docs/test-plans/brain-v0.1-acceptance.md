# Acceptance test: Rocky Brain v0.1

Record board identity, operating system, browser version, Arduino IDE version, firmware commit, wiring photo, and every failed test.

| ID | Test | Pass condition |
|---|---|---|
| BRN-01 | Inspect unpowered wiring | No connection from an I/O pin directly to 5 V; buzzer has series resistor; no 8-ohm speaker |
| BRN-02 | Apply USB power 20 times | No sound until a button or valid command requests it; mode always starts MUSICAL |
| BRN-03 | Mode-button debounce, 100 presses | At least 99 presses produce exactly one mode change; no press produces more than one change |
| BRN-04 | Phrase-button cycle | Eight presses produce the documented eight phrases in order and return to HELLO |
| BRN-05 | Exact token mapping | Browser shows the documented CSP token sequence for all eight phrase IDs |
| BRN-06 | Translation behavior | English is spoken for all eight phrases in TRANSLATED mode and none in MUSICAL mode |
| BRN-07 | Command latency | Tone begins within 250 ms of a browser phrase-button press in 19 of 20 trials |
| BRN-08 | Stop behavior | STOP command silences the buzzer within 250 ms in 19 of 20 trials |
| BRN-09 | Invalid input | `PLAY MADE_UP` returns `UNKNOWN_PHRASE` and produces no tone |
| BRN-10 | Disconnect recovery | After browser disconnect/reconnect, physical buttons still work and STATUS reports correctly |
| BRN-11 | Endurance | Complete 25 full eight-phrase cycles without lockup or unintended reset |
| BRN-12 | Sound screening | Buzzer is comfortable at 1 m and remains below the 70 dBA design target when checked with appropriate equipment |

Phone sound-meter apps may be used only for preliminary screening because they are not calibrated instruments.

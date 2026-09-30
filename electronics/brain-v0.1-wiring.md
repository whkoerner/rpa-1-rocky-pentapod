# Rocky Brain v0.1 wiring netlist

| Net | Endpoint A | Endpoint B | Notes |
|---|---|---|---|
| MODE_INPUT | Uno D2 | Mode button | `INPUT_PULLUP`; other button side is GND |
| PHRASE_INPUT | Uno D4 | Phrase button | `INPUT_PULLUP`; other button side is GND |
| AUDIO_DRIVE | Uno D9 | 220-ohm resistor | Resistor output goes to passive-buzzer `+` |
| GROUND | Uno GND | Both buttons and passive-buzzer `-` | Common reference |

The Uno's built-in D13 LED is the translation-mode indicator. No external LED is required in v0.1.

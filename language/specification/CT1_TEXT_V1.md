# CT1 — Chordic text transport V1

**Status:** Experimental desktop text transport; no change to CSP-1 v0.1.1.  
**Implementation:** `software/csp/conversation.py`, `software/rocky/audio.py`.

## Why it exists

CSP-1's six wire intents have exact fixed meanings. V1 conversation needs arbitrary English without pretending that a greeting token means a paragraph. CT1 carries validated UTF-8 text exactly. It is a musical text encoding, not a finished natural semantic grammar or an Arduino command protocol.

If a reply exactly equals one of the six `canonical_text` strings, TaskController uses the existing CSP wire message and five lexical notes. Other replies use CT1. Text that happens to contain words such as “move” or “stop” grants no control authority.

## Exact representation

Input: 1–384 UTF-8 bytes, nonblank, no Unicode category-C characters (including controls, surrogate code points and formatting controls). Preserve the original valid text without normalization or truncation.

Packet, in order:

| Field | Encoding |
|---|---|
| Magic/version | ASCII `CT1`, bytes `43 54 31` hex |
| Payload length | 2 bytes, unsigned big-endian |
| Text | Exact UTF-8 payload |
| Checksum | 4-byte big-endian CRC-32 as returned by Python `zlib.crc32`, over magic, length and text |

Each packet byte becomes four base-five digits, most significant first: `b = 125*d0 + 25*d1 + 5*d2 + d3`. Each digit is 0–4. Unused representations above 255 reject. Example: the magic is represented by `(0,2,3,2) (0,3,1,4) (0,1,4,4)`.

`decode_text(encode_text(text)) == text`. Decode rejects incorrect length/version, invalid digits/bytes, CRC mismatch and invalid text. No repair is guessed. CRC detects accidental corruption; it is not authentication.

## Musical rendering

Reuse the authoritative YAML's `D3+A3` phrase header, header timing and five pitch classes: D, E, F-sharp, A, B. Registered CSP phrases retain their original literal timing and monophonic token notes.

For CT1 only, four ordered voices carry the four digits in octaves 3, 4, 5 and 6. Each byte is a simultaneous 65 ms chord followed by a 15 ms rest, extended to 35 ms after every eighth byte. This new polyphonic **transport** is distinct from the unchanged monophonic CSP semantic core; never decode it as a legacy token. Octave position carries byte position only inside CT1.

Synthesis uses 22,050 Hz, mono signed 16-bit PCM, averaged sine voices, 12 ms attack and release up to 60 ms (limited to half a short chord). Default digital gain is 0.12; configuration allows 0–0.30. The average and envelope bound samples below clipping. This is not a calibrated dBA level: speaker gain, distance and equipment still determine loudness. Start computer volume low.

Maximum text produces approximately 33 seconds of audio; shorter replies are strongly encouraged. Playback is asynchronous. A new reply/replay replaces current playback. `/mute` and `/stop` stop it. WAV-only mode writes the same signal without requesting sound.

## Translation limits

The terminal displays the validated text associated with the exact deterministic representation. CT1 symbols decode reversibly; the generated waveform contains those symbols. **V1 has no microphone-to-symbol decoder.** `/translate` reads the most recent accepted response; it does not listen to a recording or guess English from tones. No acoustic recognition or human learnability performance is claimed.

Future vocabulary/prosody work may replace this verbose transport with reviewed semantic compositions. Version that separately and retain CT1 decoding for archived messages. Never reassign existing CSP lexical codes.

# CSP-1 Wire Format v0.1

Status: draft  
Scope: deterministic semantic messages between the RPA-1 Arduino brain, computer tools, and a later Raspberry Pi.

This wire format does **not** replace the existing Chordic musical token encoding in `csp_v0_1.yaml`. It is a small transport layer above it.

## Message shape

Each message is one ASCII line:

```text
C1|INTENT|ARG\n
```

Fields:

1. `C1` - wire protocol version.
2. `INTENT` - registered semantic intent.
3. `ARG` - optional argument. The field is always present and may be empty.

Example:

```text
C1|SOCIAL.HELLO|
```

The newline terminates the message.

## v0.1 registered intents

| Intent | Argument | Canonical text | Existing Chordic token |
| --- | --- | --- | --- |
| `SOCIAL.HELLO` | empty | Hello. | `SOCIAL.hello` |
| `RESPONSE.YES` | empty | Yes. | `SOCIAL.yes` |
| `RESPONSE.NO` | empty | No. | `SOCIAL.no` |
| `REQUEST.HELP` | empty | Help. | `ACTION.help` |
| `SOCIAL.THANKS` | empty | Thank you. | `SOCIAL.thank_you` |
| `SOCIAL.GOODBYE` | empty | Goodbye. | `SOCIAL.goodbye` |

The wire intent names are semantic interface names. The existing Chordic token names remain unchanged for compatibility.

## Encoding rules

- Encoding is ASCII.
- A complete message ends with LF (`\n`). A decoder may accept a single trailing CR before LF for serial-terminal compatibility.
- Fields are separated by exactly two `|` delimiters.
- Version must be exactly `C1`.
- Intent names use uppercase ASCII letters with exactly one dot between category and name.
- Intent syntax is `[A-Z]+\.[A-Z]+`.
- Arguments may be empty.
- Non-empty arguments may contain only `A-Z`, `0-9`, and `_`.
- Spaces are not allowed.
- The maximum message length before LF is 63 characters.
- Unknown intents are rejected. They are never guessed or autocorrected.
- v0.1 intents require an empty argument.

## Decoding rules

1. Remove one trailing LF, and one CR immediately before it if present.
2. Reject input longer than 63 characters before LF.
3. Split on `|`; require exactly three fields.
4. Require version `C1`.
5. Validate intent syntax.
6. Validate argument syntax.
7. Look up the intent in the registry.
8. Reject unknown intents.
9. For v0.1, reject a non-empty argument for the six registered intents.
10. Return the semantic intent and argument only after all checks pass.

## Determinism and reversibility

For every supported semantic message:

```text
decode(encode(message)) == message
```

There is one canonical wire representation for each supported message.

Arbitrary English is intentionally not reversible. For example, "Hi" and "Hello" may both be normalized by a user-interface layer to `SOCIAL.HELLO`, but CSP-1 decodes that intent to the canonical text "Hello."

## Errors

Reference error names:

- `FORMAT`
- `VERSION`
- `INTENT`
- `ARGUMENT`
- `TOO_LONG`

On any parsing error, no requested robot action may occur.

## Examples

Valid:

```text
C1|SOCIAL.HELLO|
C1|RESPONSE.YES|
C1|REQUEST.HELP|
```

Invalid:

```text
C2|SOCIAL.HELLO|
C1|social.hello|
C1|SOCIAL.HELO|
C1|SOCIAL.HELLO
C1|SOCIAL.HELLO|BAD ARG
```

## Safety boundary

This release carries semantic messages only. It does not add motors, networking, AI, autonomous behavior, or Raspberry Pi dependencies. A malformed or unsupported message must fail closed.

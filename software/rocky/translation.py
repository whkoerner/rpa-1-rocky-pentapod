"""Translation from deterministic symbols, separately checked against source English."""
from brain.contracts import CommunicationOutput
from csp.conversation import decode_text
from csp.learning import decode_phrase, unit_text
from csp.wire import decode, canonical_text


def decoded_text(output):
    if isinstance(output, CommunicationOutput):
        text = canonical_text(decode(output.csp_line))
        version = "CSP-1"
    elif output.phrase is not None:
        text, version = decode_phrase(output.phrase), "CT2"
    else:
        text, version = decode_text(output.symbols), "CT1"
    if text != output.canonical_text:
        raise ValueError(f"{version} translation does not match source English")
    return text, version


def learning_rows(output):
    if isinstance(output, CommunicationOutput):
        return [(decoded_text(output)[0], output.chordic_token)]
    decoded_text(output)
    if output.phrase is None:
        return [(output.canonical_text, "CT1 UTF-8 fallback")]
    return [(unit_text(u), u.value if u.kind == "token" else f"UTF-8 fallback ({len(u.value)} bytes)") for u in output.phrase.units]

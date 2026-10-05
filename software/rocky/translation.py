"""Translation from deterministic symbols, separately checked against source English."""
from brain.contracts import CommunicationOutput
from csp.conversation import decode_text
from csp.exp002 import Exp002Phrase, decode_phrase as decode_exp002_phrase, learning_rows as exp002_learning_rows
from csp.exp003 import Exp003Phrase, coverage as exp003_coverage, decode_phrase as decode_exp003_phrase, learning_rows as exp003_learning_rows
from csp.learning import decode_phrase, unit_text
from csp.wire import decode, canonical_text


def decoded_text(output):
    if isinstance(output, CommunicationOutput):
        text = canonical_text(decode(output.csp_line))
        version = "CSP-1"
    elif isinstance(output.phrase, Exp002Phrase):
        text, version = decode_exp002_phrase(output.phrase), "EXP-002"
    elif isinstance(output.phrase, Exp003Phrase):
        text, version = decode_exp003_phrase(output.phrase), "EXP-003"
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
    if isinstance(output.phrase, Exp002Phrase):
        return exp002_learning_rows(output.phrase)
    if isinstance(output.phrase, Exp003Phrase):
        return exp003_learning_rows(output.phrase)
    if output.phrase is None:
        return [(output.canonical_text, "CT1 UTF-8 fallback")]
    return [(unit_text(u), u.value if u.kind == "token" else f"UTF-8 fallback ({len(u.value)} bytes)") for u in output.phrase.units]


def representation_summary(output):
    """Human-readable runtime representation/fallback evidence for the terminal log."""
    if isinstance(output, CommunicationOutput):
        return "CSP-1 registered intent"
    if isinstance(output.phrase, Exp003Phrase):
        stats = exp003_coverage(output.phrase)
        return (
            f"EXP-003 semantic_tokens={stats['semantic_tokens']}; "
            f"coverage={stats['semantic_percent']:.1f}%; "
            f"fallback_spans={stats['fallback_spans']}; fallback_bytes={stats['fallback_bytes']}"
        )
    if isinstance(output.phrase, Exp002Phrase):
        semantic = sum(len(unit.tokens) for unit in output.phrase.units if unit.kind == "tokens")
        fallback = [unit for unit in output.phrase.units if unit.kind == "ct2"]
        fallback_bytes = sum(len(unit.text.encode("utf-8")) for unit in fallback)
        mode = "semantic" if not fallback else "semantic + exact CT2 fallback"
        return f"EXP-002 {mode}; semantic_tokens={semantic}; fallback_spans={len(fallback)}; fallback_bytes={fallback_bytes}"
    if output.phrase is not None:
        return "CT2 exact text representation"
    return "CT1 literal text representation"

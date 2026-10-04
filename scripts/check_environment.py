"""Standalone environment probe: invoked before importing the launcher package."""
from pathlib import Path
import sys

try:
    if sys.version_info < (3, 10) or sys.prefix == sys.base_prefix:
        raise RuntimeError("use a Python 3.10+ virtual environment")
    import yaml
    import rocky
    from csp.core import CspCodec
    expected = Path(__file__).resolve().parents[1] / "software" / "rocky"
    if Path(rocky.__file__).resolve().parent != expected:
        raise RuntimeError("Rocky is installed from a different project folder")
    CspCodec.from_default_spec()
except Exception as exc:
    print(f"Environment check failed: {exc}")
    raise SystemExit(2)
print(f"Environment OK: {sys.executable}")

"""Optional bridge runtime; source imports never install a distribution."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def configure():
    # Imported sibling code stays read-only, including its bytecode/cache.
    sys.dont_write_bytecode = True
    root = Path(os.environ.get('AECO_IFC_ROOT', ROOT.parent / 'usdaeco-ifc'))
    sys.path.insert(0, str(root / 'tools'))
    os.environ.setdefault('AECO_EXACT_CACHE', str(ROOT / '.work/exact-native'))
    os.environ.setdefault('USD_SOLID_OCCT_RUNTIME', str(ROOT.parent / 'usdSolidOcct/result-runtime'))
    from usdaeco_ifc import exact_runtime
    return exact_runtime


def unavailable_reason():
    root = Path(os.environ.get('USD_SOLID_OCCT_RUNTIME', ROOT.parent / 'usdSolidOcct/result-runtime'))
    if not root.exists():
        return 'usdSolidOcct runtime is absent; set USD_SOLID_OCCT_RUNTIME to its built runtime'
    configure().runtime_paths()  # Present but broken is a failure, never NOT RUN.
    return None


def renderer():
    if not os.environ.get('USDRECORD') and not unavailable_reason():
        os.environ['USDRECORD'] = str(configure().native_renderer())
    directory = Path(os.environ.get('USDRECORD', sys.executable)).parent
    os.environ['PATH'] = str(directory) + os.pathsep + os.environ.get('PATH', '')

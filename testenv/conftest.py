"""Run from source without an installed distribution."""
import os
from pathlib import Path
import sys
from pxr import Plug
ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT/'tools'),str(ROOT)]
Plug.Registry().RegisterPlugins(os.environ.get('CORE_PLUGIN_DIR',str(ROOT.parent/'usdaeco-core/out/plugins/usdAeco/resources')))
Plug.Registry().RegisterPlugins(str(ROOT/'usdAecoClash'))

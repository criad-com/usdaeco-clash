"""Rebuild the pinned IFC in this checkout and export the five selected bodies."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from .runtime import ROOT, configure
from .paths import scope_layer, study_root


def export_bodies(stage, elements, out):
    data = Path(os.environ['AECO_DATACENTRE_ROOT'])
    pins = json.loads((ROOT / 'dependencies.json').read_text())['repos']
    version = json.loads((data / 'library.json').read_text())['version']
    if 'v' + version != pins['datacentre']['ref']:
        raise ValueError('Exact source generator does not match the datacentre pin')
    configure()
    from usdaeco_ifc.exact import export_exact
    work = ROOT / '.work/datacentre'
    files = sorted((data/'spec').rglob('*')) + sorted((data/'src/dcbuild').rglob('*.py'))
    digest = hashlib.sha256(b''.join(p.read_bytes() for p in files if p.is_file())).hexdigest()
    source = work / 'ifc/demo-datacentre-01.ifc'
    receipt = work / 'source.sha256'
    if not source.is_file() or not receipt.is_file() or receipt.read_text() != digest:
        work.mkdir(parents=True, exist_ok=True)
        shutil.copytree(data/'spec', work/'spec', dirs_exist_ok=True)
        code = 'import sys;sys.dont_write_bytecode=True;sys.path.insert(0,sys.argv.pop(1));from dcbuild.cli import main;raise SystemExit(main())'
        environment = {k:v for k,v in os.environ.items() if k != 'PYTHONPATH'}
        process = subprocess.run([sys.executable, '-c', code, str(data/'src'), 'build-ifc',
                                  '--variant', 'clash', '--out', 'ifc', '--manifest-dir', 'manifests'],
                                 cwd=work, env=environment, text=True, capture_output=True, timeout=240)
        if process.returncode:
            raise RuntimeError('Pinned IFC generation failed: ' + process.stderr[-2000:])
        receipt.write_text(digest)
    report = export_exact(source, data/'dist/clash/dc.usda', out,
                          identities={p.GetAttribute('aeco:id').Get() for p in elements.values()}, deflection=.0001)
    if report['failed'] or report['exact'] != len(elements):
        raise ValueError('Exact export did not produce every selected body: ' + json.dumps(report['perClass']))
    root = study_root(stage)
    if str(root) != '/':
        from pxr import Sdf
        for filename in ('exact.usda', 'twins.usda'):
            layer = Sdf.Layer.FindOrOpen(str(out / filename))
            scope_layer(layer, root)
            layer.Save()
    return report

#!/usr/bin/env python3
"""Compose the pinned clash stage, measure, validate and publish on request."""
import argparse
import os
from pathlib import Path
import sys
import json
import shutil
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(Path(os.environ.get('TOOLCHAIN_DIR',ROOT.parent/'usdaeco-toolchain'))/'tools'),str(ROOT/'tools'),str(ROOT)]
from usdaeco_check.example import run_example
from usdaeco_clash.example import derive
from usdaeco_clash.cli import register


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--publish',action='store_true')
    args=parser.parse_args()
    if not os.environ.get('AECO_DATACENTRE_ROOT'):
        parser.error('AECO_DATACENTRE_ROOT is required for this pinned example')
    register()
    from usdaeco_clash.runtime import renderer,unavailable_reason
    renderer()
    example=Path(__file__).parent
    manifest=run_example(example,derive,variant='clash',publish=args.publish,keywords=[])
    if not unavailable_reason():
        from usdaeco_render import render
        previous=os.environ.get('USDIMAGINGGL_ENGINE_ENABLE_SCENE_INDEX')
        os.environ['USDIMAGINGGL_ENGINE_ENABLE_SCENE_INDEX']='1'
        try:
            records=render(example/'out/example.usda',output=example/'out/guides',
                           cameras=example/'out/wireframe-view.usda',views=['wireframe'],purposes='guide,proxy,render')
        finally:
            if previous is None:os.environ.pop('USDIMAGINGGL_ENGINE_ENABLE_SCENE_INDEX',None)
            else:os.environ['USDIMAGINGGL_ENGINE_ENABLE_SCENE_INDEX']=previous
        for record in records:
            name='wireframe.png'
            shutil.copyfile(example/'out/guides'/Path(record['path']).name,example/'out/renders'/name)
            record['path']='renders/'+name
            if args.publish:shutil.copyfile(example/'out/renders'/name,example/'renders'/name)
        manifest['renders'].extend(records)
        (example/'out/manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
        if args.publish:shutil.copyfile(example/'out/manifest.json',example/'manifest.json')


if __name__=='__main__':
    main()

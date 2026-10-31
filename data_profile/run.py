"""Run stages sequentially; stage 2 reconciliation gates all later analysis."""
import os
os.environ.setdefault('POLARS_MAX_THREADS','2')
os.environ.setdefault('OMP_NUM_THREADS','2')
os.environ.setdefault('MPLBACKEND','Agg')

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime

from .src.common import ROOT, OUT, DERIVED, json_save, mkdirs


def commit_stage(stage):
    subprocess.run(['git','add','.gitignore','data_profile','outputs'],cwd=ROOT,check=True)
    staged=subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT)
    if staged.returncode==1:
        subprocess.run(['git','commit','-m',f'Complete profiling stage {stage}'],cwd=ROOT,check=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--all',action='store_true')
    parser.add_argument('--stage',choices=['ingest','labels','merchants','consistency','purity','descriptive','annotation','finalize'])
    parser.add_argument('--no-commit',action='store_true')
    parser.add_argument('--reuse-canonical',action='store_true')
    args=parser.parse_args();mkdirs();start=time.perf_counter()
    stages=['ingest','labels','merchants','consistency','purity','descriptive','annotation','finalize'] if args.all else [args.stage or 'ingest']
    timings=json.loads((DERIVED/'stage_timings.json').read_text()) if (DERIVED/'stage_timings.json').exists() else {}
    for stage in stages:
        if stage=='ingest' and args.reuse_canonical:
            from .src.ingest import verify_reconciliation
            verify_reconciliation();continue
        print(f'START {stage}',flush=True);stage_start=time.perf_counter()
        if stage=='ingest':
            from .src.ingest import ingest
            ingest()
        else:
            from .src.ingest import verify_reconciliation
            verify_reconciliation()
            if stage=='labels':
                from .src.labels import run
            elif stage=='merchants':
                from .src.merchants import run
            elif stage=='consistency':
                from .src.consistency import run
            elif stage=='purity':
                from .src.purity import run
            elif stage=='descriptive':
                from .src.descriptive import run
            elif stage=='annotation':
                from .src.annotation import run
            else:
                from .src.finalize import run
            run()
        timings[stage]=time.perf_counter()-stage_start
        json_save(DERIVED/'stage_timings.json',timings)
        json_save(OUT/'run_state.json',{'last_completed_stage':stage,'timings_seconds':timings,'updated':datetime.now().isoformat()})
        if not args.no_commit:commit_stage(stage)
        print(f'COMPLETE {stage}: {timings[stage]:.1f}s',flush=True)
    print(f'RUN COMPLETE: {time.perf_counter()-start:.1f}s',flush=True)


if __name__=='__main__':
    main()

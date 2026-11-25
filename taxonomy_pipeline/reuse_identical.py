"""Reuse labels only for byte-identical CSVs from the same source."""
import json,shutil
from collections import defaultdict
from run import BASE,ROOT,DEST,ANALYSIS,digest,fileid,primary,save_json,source_id

def main():
    rows=json.loads((ANALYSIS/'source_baseline.json').read_text(encoding='utf-8'))
    groups=defaultdict(list);rulehash=digest(BASE/'taxonomy_pipeline/rules.py')
    for r in rows:
        if r['source_file'].endswith('.csv'):groups[(source_id(r['source_file']),r['sha256'])].append(r)
    for candidates in groups.values():
        if len(candidates)<2:continue
        original=None;meta=None
        for r in sorted(candidates,key=lambda r:not primary(ROOT/r['source_file'])):
            mp=ANALYSIS/'manifests'/f"{fileid(r['source_file'])}.json"
            if mp.exists():
                m=json.loads(mp.read_text(encoding='utf-8'))
                if m.get('rules_sha256')==rulehash:original=r;meta=m;break
        if not original:continue
        for r in candidates:
            rel=r['source_file'];fid=fileid(rel);mp=ANALYSIS/'manifests'/f'{fid}.json'
            if rel==original['source_file'] or mp.exists() and json.loads(mp.read_text(encoding='utf-8')).get('rules_sha256')==rulehash:continue
            assert digest(DEST/original['source_file'])==meta['output_sha256']
            out=DEST/rel;out.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(DEST/original['source_file'],out)
            shutil.copyfile(ANALYSIS/'audit'/f"{meta['file_id']}.parquet",ANALYSIS/'audit'/f'{fid}.parquet')
            shutil.copytree(ANALYSIS/'files'/meta['file_id'],ANALYSIS/'files'/fid,dirs_exist_ok=True)
            clone={**meta,'source_file':rel,'file_id':fid,'read_path':r['read_path'],'is_primary_input':primary(ROOT/rel),'reused_identical_file':original['source_file']}
            save_json(mp,clone);print('REUSED '+rel,flush=True)
if __name__=='__main__':main()

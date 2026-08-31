"""Final public/private schema and released-annotation hygiene audit."""
from __future__ import annotations
import csv, json
from collections import Counter
from pathlib import Path
from benchmark_validation_utils import feature_association

ROOT=Path(__file__).resolve().parent
PUBLIC_FIELDS=['question_id','task','image','prompt']

def records(folder):
 return [json.loads(x) for x in (folder/'annotations.jsonl').read_text(encoding='utf8').splitlines() if x]
def remove_polyhedron_difficulty(folder):
 rows=records(folder);removed=0;values=[]
 for row in rows:
  if 'difficulty_score' in row: values.append(row.pop('difficulty_score'));removed+=1
 (folder/'annotations.jsonl').write_text(''.join(json.dumps(r,sort_keys=True,separators=(',',':'))+'\n' for r in rows),encoding='utf8')
 # Remove the diagnostic from answer-side flattened metadata as well.
 for name in ('dataset_final.jsonl',):
  path=folder/name
  if not path.exists():continue
  out=[]
  for line in path.read_text(encoding='utf8').splitlines():
   row=json.loads(line)
   if isinstance(row.get('metadata'),str):
    try:meta=json.loads(row['metadata']);meta.pop('difficulty_score',None);row['metadata']=json.dumps(meta,sort_keys=True,separators=(',',':'))
    except json.JSONDecodeError:pass
   out.append(row)
  path.write_text(''.join(json.dumps(r,separators=(',',':'))+'\n' for r in out),encoding='utf8')
 path=folder/'dataset_final.csv'
 if path.exists():
  with path.open(encoding='utf-8-sig',newline='') as f: data=list(csv.DictReader(f));fields=list(data[0]) if data else []
  for row in data:
   if 'metadata' in row:
    try:meta=json.loads(row['metadata']);meta.pop('difficulty_score',None);row['metadata']=json.dumps(meta,sort_keys=True,separators=(',',':'))
    except json.JSONDecodeError:pass
  with path.open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(data)
 return removed,values
def schema(path):
 with path.open(encoding='utf-8-sig',newline='') as f:return next(csv.reader(f))
def main():
 poly=ROOT/'polyhedron_dataset_3000';removed,difficulty=remove_polyhedron_difficulty(poly)
 previous=json.loads((poly/'validation_metrics.json').read_text(encoding='utf8'))
 historical_difficulty=previous.get('difficulty_score_build_diagnostic') or previous.get('continuous_distributions',{}).get('difficulty_score',{})
 folders=sorted(p for p in ROOT.iterdir() if p.is_dir() and (p/'annotations.jsonl').exists())
 suite={};fail=[]
 for folder in folders:
  entry={'question_set.csv':schema(folder/'question_set.csv'),'annotations.jsonl':sorted(records(folder)[0].keys()),'answer_key.csv':schema(folder/'answer_key.csv')}
  entry['public_schema_pass']=entry['question_set.csv']==PUBLIC_FIELDS
  if not entry['public_schema_pass']:fail.append(folder.name)
  suite[folder.name]=entry
 rows=records(poly);answers={str(l):[str(r['questions'][l-1]['ground_truth']) for r in rows] for l in range(1,6)}
 canvas=[r['canvas_size'] for r in rows]
 canvas_v={l:feature_association(canvas,a)[0] for l,a in answers.items()}
 combo=records(ROOT/'combination3d_dataset_3000')
 combo_v={}
 combo_values={'target_cube_count':[r['target_cube_count'] for r in combo],'height_z_layers':[max(cube[2] for cube in r['target_cubes'])+1 for r in combo]}
 for feature,values in combo_values.items():
  combo_v[feature]={str(l):feature_association(values,[str(r['questions'][l-1]['ground_truth']) for r in combo])[0] for l in range(1,6)}
 report={'public_rule':'question_set.csv is the only model-facing artifact; all other data files are answer-key-side','per_dataset_fields':suite,'failures':fail,'polyhedron':{'difficulty_score_absent_from_released_annotations':all('difficulty_score' not in r for r in rows),'difficulty_score_removed_records_this_run':removed,'difficulty_score_validation_summary':historical_difficulty,'canvas_size_bias_corrected_cramers_v':canvas_v,'cause':'uncorrected sparse-table bias from 1801 size-pair categories in 3000 records; dimensions are seeded independently of cyclic solid identity','regenerated':False},'combination3d':{'post_fix_bias_corrected_cramers_v':combo_v,'classification':{'target_cube_count':{'L4':'definitional: L4 explicitly requests target count','L5':'non-definitional but answer-key-side, never in question_set.csv'},'height_z_layers':{'L4':'definitional: L4 explicitly requests height','L5':'non-definitional but answer-key-side, never in question_set.csv'}}}}
 (ROOT/'release_hygiene_audit.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n',encoding='utf8')
 print(f'datasets={len(folders)} public_schema_failures={fail} poly_difficulty_removed={removed}')
if __name__=='__main__':main()

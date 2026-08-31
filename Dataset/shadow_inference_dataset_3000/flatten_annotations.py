import argparse,csv,json
from collections import Counter
from pathlib import Path
TASKS={1:'Image Description',2:'Basic Relational Reasoning',3:'Comparative Reasoning',4:'Compound Reasoning'}
def main():
 p=argparse.ArgumentParser();p.add_argument('annotations',type=Path);a=p.parse_args();data=[json.loads(x) for x in a.annotations.read_text(encoding='utf8').splitlines()];rows=[]
 for r in data:
  meta=json.dumps({k:r[k] for k in ('difficulty_score','num_objects','has_inconsistent_shadow','seed')},sort_keys=True,separators=(',',':'))
  for q in r['questions']:rows.append({'task':TASKS[q['difficulty_level']],'image':Path(r['image_path']).name,'prompt':q['question_text'],'groundtruth':str(q['ground_truth']),'metadata':meta})
 out=a.annotations.parent;cols=['task','image','prompt','groundtruth','metadata']
 with (out/'dataset_final.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=cols,lineterminator='\n');w.writeheader();w.writerows(rows)
 with (out/'dataset_final.jsonl').open('w',encoding='utf8',newline='\n') as f:
  for r in rows:f.write(json.dumps(r,separators=(',',':'))+'\n')
 c=Counter(r['task'] for r in rows);print(f'Images: {len(data)}\nRows: {len(rows)}');[print(f'{x}: {c[x]}') for x in TASKS.values()];assert len(rows)==4*len(data);print('Sanity check: PASS')
if __name__=='__main__':main()

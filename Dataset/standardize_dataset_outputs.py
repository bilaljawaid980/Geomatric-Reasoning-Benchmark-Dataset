"""Write the standard five-level flat outputs and build manifest for a dataset."""
import argparse,csv,json,subprocess
from pathlib import Path

TASKS={1:'Image Description',2:'Basic Relational Reasoning',3:'Comparative Reasoning',4:'Compound Reasoning',5:'Extrapolative/Counterfactual Reasoning'}

def main():
    p=argparse.ArgumentParser();p.add_argument('dataset_dir',type=Path);a=p.parse_args();root=a.dataset_dir
    rows=[json.loads(line) for line in (root/'annotations.jsonl').read_text(encoding='utf-8').splitlines()]
    flat=[]
    for record in rows:
        if len(record.get('questions',[]))!=5 or [q['difficulty_level'] for q in record['questions']]!=[1,2,3,4,5]:raise ValueError(f"{record.get('id')}: not five levels")
        meta={k:v for k,v in record.items() if k not in {'questions','image_path','image','id'} and not isinstance(v,(dict,list))}
        for q in record['questions']:
            flat.append({'question_id':q['question_id'],'task':TASKS[q['difficulty_level']],'image':Path(record.get('image_path',record.get('image'))).name,'prompt':q['question_text'],'groundtruth':str(q['ground_truth']),'metadata':json.dumps(meta,sort_keys=True,separators=(',',':'))})
    fields=['task','image','prompt','groundtruth','metadata']
    with (root/'dataset_final.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:r[k] for k in fields} for r in flat)
    with (root/'dataset_final.jsonl').open('w',encoding='utf-8',newline='\n') as f:
        for r in flat:f.write(json.dumps({k:r[k] for k in fields},ensure_ascii=False,separators=(',',':'))+'\n')
    public=['question_id','task','image','prompt']
    with (root/'question_set.csv').open('w',encoding='utf-8-sig',newline='') as fq,(root/'answer_key.csv').open('w',encoding='utf-8-sig',newline='') as fa:
        q=csv.DictWriter(fq,fieldnames=public);ans=csv.DictWriter(fa,fieldnames=public+['groundtruth']);q.writeheader();ans.writeheader()
        for r in flat:q.writerow({k:r[k] for k in public});ans.writerow({k:r[k] for k in public+['groundtruth']})
    try:commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    except Exception:commit='working-tree'
    manifest={'dataset_version':rows[0].get('dataset_version','legacy-current'),'generator_commit':commit,'images':len(rows),'questions':len(flat),'current_build_layout':'unsuffixed','constraint_source':'generator constants and validation metrics','question_set_fields':public}
    (root/'build_manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(f"{root.name}: {len(rows)} images, {len(flat)} questions")
if __name__=='__main__':main()

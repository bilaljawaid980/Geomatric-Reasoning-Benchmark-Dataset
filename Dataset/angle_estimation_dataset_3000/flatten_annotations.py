import argparse,csv,json
from collections import Counter
from pathlib import Path
TASKS={1:'Image Description',2:'Angle Estimation',3:'Structural Reasoning',4:'Compound Reasoning'};META=('difficulty_score','scene_type','canvas_size','seed')
def flatten(root):
    root=Path(root);rows=[];images=0;bad=[]
    for line in (root/'annotations.jsonl').open(encoding='utf8'):
        item=json.loads(line);images+=1;qs=item.get('questions',[])
        if len(qs)!=4:bad.append(item['id'])
        metadata=json.dumps({k:item[k] for k in META},separators=(',',':'))
        for q in qs:rows.append({'task':TASKS[q['difficulty_level']],'image':Path(item['image_path']).name,'prompt':q['question_text'],'groundtruth':str(q['ground_truth']),'metadata':metadata})
    fields=('task','image','prompt','groundtruth','metadata')
    with (root/'dataset_final.csv').open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    with (root/'dataset_final.jsonl').open('w',encoding='utf8',newline='\n') as f:
        for row in rows:f.write(json.dumps(row,separators=(',',':'))+'\n')
    with (root/'dataset_final.csv').open(encoding='utf-8-sig',newline='') as f:readback=sum(1 for _ in csv.DictReader(f))
    counts=Counter(r['task'] for r in rows);print(f'Images read: {images}\nTotal rows written: {len(rows)}\nCSV rows re-read: {readback}')
    for task,count in sorted(counts.items()):print(f'{task}: {count}')
    print('Images without exactly 4 questions: '+(', '.join(bad) if bad else 'none'))
    if readback!=images*4 or bad:raise SystemExit(1)
def main():p=argparse.ArgumentParser();p.add_argument('--dataset-dir',default='.');flatten(p.parse_args().dataset_dir)
if __name__=='__main__':main()

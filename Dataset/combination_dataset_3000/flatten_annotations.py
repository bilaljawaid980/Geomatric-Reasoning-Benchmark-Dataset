import argparse,csv,json
from collections import Counter
from pathlib import Path

TASKS={1:'Image Description',2:'2D Combination',3:'Comparative Reasoning',4:'Compound Reasoning'}
META=('difficulty_score','target_cell_count','correct_answer_choice','canvas_size','seed')

def plain(value):
    if isinstance(value,list):return ', '.join(map(str,value))
    if isinstance(value,dict):return ', '.join(f'{k}: {v}' for k,v in value.items())
    return str(value)

def flatten(root):
    root=Path(root);rows=[];images=0;bad=[]
    for line in (root/'annotations.jsonl').open(encoding='utf8'):
        item=json.loads(line);images+=1;qs=item.get('questions',[])
        if len(qs)!=4:bad.append(item['id'])
        meta=json.dumps({k:item[k] for k in META if k in item},separators=(',',':'))
        for q in qs:
            rows.append({'task':TASKS[q['difficulty_level']],'image':Path(item['image_path']).name,'prompt':q['question_text'],'groundtruth':plain(q['ground_truth']),'metadata':meta})
    fields=['task','image','prompt','groundtruth','metadata']
    with (root/'dataset_final.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    with (root/'dataset_final.jsonl').open('w',encoding='utf8',newline='\n') as f:
        for row in rows:f.write(json.dumps(row,ensure_ascii=False,separators=(',',':'))+'\n')
    with (root/'dataset_final.csv').open(encoding='utf-8-sig',newline='') as f:readback=sum(1 for _ in csv.DictReader(f))
    counts=Counter(r['task'] for r in rows)
    print(f'Images read: {images}\nTotal rows written: {len(rows)}\nCSV rows re-read: {readback}')
    for task,count in sorted(counts.items()):print(f'{task}: {count}')
    print('Images without exactly 4 questions: '+(', '.join(bad) if bad else 'none'))
    if readback!=len(rows) or len(rows)!=images*4 or bad:raise SystemExit(1)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--dataset-dir',default='.');flatten(parser.parse_args().dataset_dir)
if __name__=='__main__':main()

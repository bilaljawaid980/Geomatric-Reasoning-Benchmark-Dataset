import argparse,csv,json
from pathlib import Path
TASKS={1:'Image Description',2:'3D Combination',3:'Comparative Reasoning',4:'Compound Reasoning',5:'Extrapolative/Counterfactual Reasoning'}
def flatten(root):
 root=Path(root);data=[json.loads(x) for x in (root/'annotations.jsonl').read_text(encoding='utf8').splitlines()];final=[];questions=[];answers=[]
 for item in data:
  if len(item['questions'])!=5:raise ValueError(f"{item['id']}: expected five questions")
  meta=json.dumps({k:item[k] for k in ('dataset_version','difficulty_score','target_cube_count','correct_answer_choice','vertical_axis','seed')},sort_keys=True,separators=(',',':'))
  for q in item['questions']:
   base={'question_id':q['question_id'],'task':TASKS[q['difficulty_level']],'image':Path(item['image_path']).name,'prompt':q['question_text']};questions.append(base);answers.append({**base,'groundtruth':str(q['ground_truth']),'answer_format':q['answer_format']});final.append({'task':base['task'],'image':base['image'],'prompt':base['prompt'],'groundtruth':str(q['ground_truth']),'metadata':meta})
 def write(name,rows,fields):
  with (root/name).open('w',encoding='utf-8-sig',newline='') as f:w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows)
 write('dataset_final.csv',final,['task','image','prompt','groundtruth','metadata']);write('question_set.csv',questions,['question_id','task','image','prompt']);write('answer_key.csv',answers,['question_id','task','image','prompt','groundtruth','answer_format'])
 with (root/'dataset_final.jsonl').open('w',encoding='utf8',newline='\n') as f:
  for row in final:f.write(json.dumps(row,separators=(',',':'))+'\n')
 print(f'Images: {len(data)}; rows: {len(final)}')
def main():
 p=argparse.ArgumentParser();p.add_argument('--dataset-dir',default='.');flatten(p.parse_args().dataset_dir)
if __name__=='__main__':main()

"""Verify and record the final standard repository layout."""
import csv,json,re
from pathlib import Path

root=Path(__file__).resolve().parent
required={'images','annotations.jsonl','question_set.csv','answer_key.csv','dataset_final.csv','dataset_final.jsonl','build_manifest.json','validation_report.txt','validation_metrics.json','generation_stats.json','README.md'}
errors=[];lines=[]
datasets=sorted(d for d in root.iterdir() if d.is_dir() and (d/'annotations.jsonl').exists())
for d in datasets:
    rows=[json.loads(x) for x in (d/'annotations.jsonl').read_text(encoding='utf-8').splitlines()]
    names={p.name for p in d.iterdir() if p.name!='__pycache__'};missing=required-names
    if missing:errors.append(f'{d.name}: missing {sorted(missing)}')
    manifest=json.loads((d/'build_manifest.json').read_text(encoding='utf-8'))
    open_files=set(manifest.get('open_question_files',[]))
    open_support={'build_open_questions.py','validate_open_questions.py','open_validation_metrics.json','open_validation_report.txt'} if open_files else set()
    allowed=required | open_files | open_support | {name for name in names if re.fullmatch(r'(generate|validate|flatten)_.+\.py',name)}
    extra=names-allowed
    if extra:errors.append(f'{d.name}: unexpected {sorted(extra)}')
    for prefix in ('generate_','validate_','flatten_'):
        standard_scripts=[name for name in names if name.startswith(prefix) and name.endswith('.py') and name!='validate_open_questions.py']
        if len(standard_scripts)!=1:
            errors.append(f'{d.name}: expected exactly one {prefix}*.py')
    if open_files:
        if not open_files <= names:errors.append(f'{d.name}: missing declared open-question files')
        with (d/'open_questions.csv').open(encoding='utf-8-sig',newline='') as f:
            reader=csv.reader(f);open_header=next(reader);open_questions=sum(1 for _ in reader)
        if open_header!=['question_id','image','prompt'] or open_questions!=len(rows):errors.append(f'{d.name}: open_questions contract')
    if any(re.search(r'_v\d+$',p.stem) for p in d.iterdir() if p.is_file()):errors.append(f'{d.name}: version-suffixed top-level file')
    images=sum(1 for _ in (d/'images').glob('*.png'))
    if images!=len(rows):errors.append(f'{d.name}: images {images}/{len(rows)}')
    with (d/'question_set.csv').open(encoding='utf-8-sig',newline='') as f:
        reader=csv.reader(f);header=next(reader);questions=sum(1 for _ in reader)
    if header!=['question_id','task','image','prompt'] or questions!=5*len(rows):errors.append(f'{d.name}: question_set contract')
    top=sorted(p.name+('/' if p.is_dir() else '') for p in d.iterdir())
    lines.append(f'{d.name}: '+', '.join(top))
archive_pngs=sum(1 for p in root.rglob('*.png') if 'archive' in {x.lower() for x in p.relative_to(root).parts})
archive_dirs=sum(1 for p in root.rglob('archive') if p.is_dir())
if archive_pngs:errors.append(f'archive PNGs: {archive_pngs}')
if archive_dirs:errors.append(f'archive directories: {archive_dirs}')
report=['GRIP-Benchmark-34 Final Release Check','='*40,f'Datasets: {len(datasets)}',f'Archive directories: {archive_dirs}',f'Archive PNGs: {archive_pngs}',f'Errors: {len(errors)}']
report+=errors or ['None'];report+=['','Final per-dataset top-level listings:']+lines
(root/'final_release_check.txt').write_text('\n'.join(report)+'\n',encoding='utf-8')
print('\n'.join(report[:8]))
raise SystemExit(bool(errors))

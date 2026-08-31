"""Apply the final release table/version and limitations documentation."""
import json,re
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'Dataset'
readme=ROOT/'README.md';text=readme.read_text(encoding='utf8')
lines=text.splitlines()
inside=False
for i,line in enumerate(lines):
 if line.startswith('| Dataset | Geometry class |'):
  lines[i]=line.replace('| Images |','| Version | Images |');inside=True;continue
 if inside and line.startswith('|---|'):
  lines[i]=line.replace('|---:|','|---|---:|',1);continue
 if inside and line.startswith('| **Total**'):
  lines[i]=line.replace('| **100,000** |','| — | **100,000** |');inside=False;continue
 if inside and line.startswith('| ['):
  match=re.search(r'\(Dataset/([^/]+)/\)',line)
  if match:
   version=json.loads((DATA/match.group(1)/'build_manifest.json').read_text(encoding='utf8'))['dataset_version']
   parts=line.split('|');parts.insert(3,f' {version} ');lines[i]='|'.join(parts)
text='\n'.join(lines)+'\n'

high=[]
constant=[]
for folder in sorted(p for p in DATA.iterdir() if p.is_dir() and (p/'annotations.jsonl').exists()):
 rows=[json.loads(x) for x in (folder/'annotations.jsonl').read_text(encoding='utf8').splitlines() if x]
 for level in range(1,6):
  counts=Counter(str(r['questions'][level-1]['ground_truth']) for r in rows);baseline=max(counts.values())/len(rows)
  if baseline>=.60:
   entry=(folder.name,level,baseline)
   high.append(entry)
   if baseline==1:constant.append(entry)
limitations='\n'.join(f'- `{name}` Level {level}: **{value:.1%}**' for name,level,value in high)
release=f'''## 6. Release use, validation, and limitations

### Public and private files

`question_set.csv` is the only model-facing dataset file. It contains exactly `question_id`, `task`, `image`, and `prompt`. `annotations.jsonl`, `answer_key.csv`, `dataset_final.csv`, and `dataset_final.jsonl` are private answer-key-side artifacts and contain ground truth or scene metadata that may directly reveal answers. **Never provide `annotations.jsonl` to a tested model.**

### Validation methodology

Validators independently re-derive answers from stored geometry, inspect final PNGs for recoverable question-dependent quantities, run bias-corrected Cramér's V feature/answer audits, exercise constraints with violating and boundary guard-injection cases, and report constant-answer baselines. Accuracy should be interpreted relative to the reported baseline rather than as an isolated percentage.

### Depth/height scope

`depth_height_dataset_3000` is deliberately split: 1,500 scenes contain perspective-based size and vertical-position cues for projective depth ordering, while 1,500 are flat stack-height counting scenes. The whole category should not be described as exclusively projective.

### Levels with constant-answer baseline at or above 60%

{limitations}

Six levels are structurally constant at 100% and therefore carry no discriminative signal: `cube_net` L1 (every cube net has six faces), `gear_train` L2 (meshed gears counter-rotate), `optical_illusion` L1 (two elements are always compared), `orthographic` L5, `polyhedron` L5 (removing a face opens the surface), and `symmetry_pattern` L5. Report results as accuracy above baseline, and do not treat performance on these levels as evidence of reasoning ability.

'''
text=text.replace('## 6. Folder structure',release+'## 7. Folder structure')
readme.write_text(text,encoding='utf8')
print(f'high_baseline_levels={len(high)} constant_levels={len(constant)}')

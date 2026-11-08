# Five-model handoff: pre-send report

This release supersedes the earlier handoffs. Use **GRIP_FIVE_MODEL_HANDOFF.zip**,
not the older BLOCKED or six-model archives. Historical local artifacts were
preserved; they are not members of this ZIP. No dataset/source files were changed.

## Contents and size

- ZIP: **83,518,448 bytes** (83.52 MB decimal).
- Uncompressed package: **117,115,811 bytes** (117.12 MB decimal), 2,917 files.
- Evaluation: **2,665 unique images**, 79,614,546 bytes of original PNG data.
- Smoke: **179 unique images**; package total **2,844 unique images**.
- Removed from the new package: the discontinued sixth model, its assembly
  script, both extra-E1 manifests (including 2,620 additional requests), and
  **2,511 images** used only for that E1 sample. No reference to that model remains
  in the package, including configuration and inventories.
- Phase B row counts remain dependent on actual returned Round-1 responses.
  No open-weight inference or hosted rerun was performed.

| Model | Smoke | E3 Phase A | E4 Phase A | Additional E1 |
| --- | ---: | ---: | ---: | ---: |
| Qwen3-VL-8B-Instruct | 847 | 3,400 | 2,000 | 0 |
| Qwen3-VL-8B-Thinking | 847 | 3,400 | 2,000 | 0 |
| Molmo2-8B | 847 | 3,400 | 2,000 | 0 |
| InternVL3.5-8B | 847 | 3,400 | 2,000 | 0 |
| DeepSeek-VL2-Small | 847 | 3,400 | 2,000 | 0 |
| Total | 4,235 | 17,000 | 10,000 | 0 |

## Literal pre-send results

**a. Evaluation leak check — PASS.** Searched field names:
`ground_truth`, `acceptance_set`, `tolerance`, `correct`, `prediction`,
`score_mode`, `solution`, `key`, `derivation`, `difficulty_score`.
`banned_fields_found: []`; `annotations_jsonl_files: 0`;
`PNG_text_or_EXIF_metadata_files: 0`. Public prose remains unchanged, including
59 prompts saying “tolerance” and 105 saying “correct”; these are not private
fields. No evaluation annotation-derived answer files are included.

**b. Hosted prompt parity — PASS.** `rows_compared: 5400`;
`rows_differing: 0` (E3: 3,400/0; E4: 2,000/0). UTF-8 field contents compared
byte-for-byte with saved hosted `prompt_sent` records.

**c. Disjointness — PASS.** Compared evaluation 2,665 image IDs / 5,400 question
IDs with smoke 179 image IDs / 847 question IDs; intersections **0 / 0**. Also
checked smoke against 100,000 released image IDs and 600,000 released question
IDs; intersections **0 / 0**. No generated smoke ID collides with a release ID.

**d. Counts — PASS.** Exactly five target models; E3 3,400, E4 2,000 and smoke 847
per model, as in the table and `INTEGRITY.json`. Only E3/E4 evaluation manifests
are shipped. Phase B counts/hashes will be written after genuine Round 1.

**e. Images and size — PASS.** 2,665 evaluation + 179 smoke = 2,844 unique images;
all 2,665 evaluation PNG hashes match their stored hosted-source files. The 12
original scorer/construction source hashes also remain unchanged.

**f. Credential/path checks — PASS.** `.env` files **0**; credential-pattern
matches **0**; credential-key/token files **0**; absolute ZIP member paths **0**;
concrete absolute filesystem paths in parsed values/source literals **0**.
Generic programming words “key” and “token” are not credentials, and remain in
exact scorer source/decoding documentation. The private deterministic ID seed
is not an authentication secret. Dataset answers are intentionally included only
under `private/`, per the approved architecture.

**g. Issued filenames.** `README.md`, `config.json`, `INTEGRITY.json`,
`scoring/tolerance_config.json`, `scoring/pins.json`,
`requirements-scoring.lock.txt`.

## Workflow and safeguards

The README contains setup, five checkpoint-specific serving commands, immutable
weight download/revision capture, every smoke/Phase A/Phase B command, progress
and resume, completeness checks and an allowlisted return-archive command.
Contact names/addresses are intentionally omitted. Smoke evidence goes back
through the existing delivery channel; the developer must WAIT for the sender's
explicit approval before full inference. The runner enforces an approval record.

The runner's file-open guard was tested against direct and traversal reads of
`private/`; both were denied. Public integrity checks never open private data.
Only the Phase B builder and smoke scorer read private answers. Modified scorer
and configuration files are refused at startup, with no override. The seven
historical-hosts-plus-single-target peer rule was asserted across **10,000**
model/image combinations. Phase B has exactly four fields and relative image
paths. Offline hosted-response replays produced deterministic manifests in two
independent builds; E3 assertions matched the archived hosted construction.
Replay fixtures and synthetic response files are local tests, not ZIP contents
and not claimed as open-weight model results.

Offline test suite literal result: **Ran 14 tests — OK**. This includes a
synthetic complete 25-run return/ZIP test, verbatim transport/history checks,
smoke-gate refusal before any request, and rejection of placeholder approvals.

The return includes raw JSONLs, Phase B CSVs/sidecars, provenance, smoke scores,
resolved configs, environment/hardware/revision evidence and verification output.
No final Round-2 outcome scoring is assigned to the developer; all fifteen models
are scored centrally. Central Phase B regeneration/byte-diff remains mandatory.

## Remaining disclosed limitations

The smoke set is still partial: 179 images / 847 questions across 30 domains,
not the requested 204 / 1,020 across 34. Generator failures/missing fifth-question
retrofits are recorded in `smoketest/STATUS.json`; no substitutes were invented.
The approval gate explicitly covers this limitation. Serving recipes are based
on official model/vLLM documentation, not hardware-tested inference here.
Historical open-weight runtime/decoding details were not recorded; the supplied
resolved smoke recipe is explicitly proposed, not presented as historical fact.
After dropping the discontinued model, only one shipped checkpoint is explicitly
named Thinking; the guide does not invent a second one.

Documentation lookup and the authorized Git operations use the network. Model
inference/API requests during build and tests: **0**. No hosted response, arm,
input image or original scorer was modified.

## Final ZIP tree (answers marked)

```text
GRIP_FIVE_MODEL_HANDOFF.zip
  README.md
  config.json
  INTEGRITY.json
  STATUS.json
  LICENSE
  requirements-scoring.lock.txt
  run_local.py
  build_phase_b.py
  compare_phase_b.py
  verify.py
  workflow.py
  prepare_models.py
  evaluation/
    E3_phase_a.csv
    E4_phase_a.csv
    images/<domain>/<image_id>.png       2,665 originals; no answers
  private/                             ANSWERS AND CONSTRUCTION INPUTS
    e3_closed_manifest.csv
    e4_answers.jsonl
    gauge_scales.json
    hosted_peers.jsonl
    missing_hosted_peers.json
    construction_seed.json
    smoke_answers.jsonl
    smoke_scenes/<domain>/fresh_scenes.jsonl
  scoring/
    assignment_scorer.py
    tolerance_config.json
    pins.json
    vendor/                            Exact code; no item answer tables
  smoketest/
    images/<domain>/<image_id>.png      179 fresh originals
    manifest.csv                       847 public questions
    score_smoke.py                      Reads private smoke labels
    hosted_reference.csv
    STATUS.json
```

Only `private/` contains per-item answers/scenes. Integrity hashes are not
credentials or answer values. File inventory entries do not expose private
answer contents outside that directory.

## Integrity

ZIP SHA-256:
`51661f5c736941d50c4b265b5f90ba5b7331fa4f39553bb92149df44b683e4cd`

INTEGRITY.json SHA-256:
`795fc8757f5194d91b020d6afdac8a14b03e3ac745423399253f6340907d8e84`

Scorer SHA-256:
`cf4659a5c439ef3758c6ac360b198b79056fac355024d932783126d9d722fb77`

Tolerance configuration SHA-256:
`b04cfadbdf0c83a694cef5a2b09083b2c2b7c92f39072dc736933ce17420474b`

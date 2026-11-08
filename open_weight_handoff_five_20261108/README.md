# GRIP: five-model E3/E4 developer guide

## 1. What you are running and what we need back

Run image-based inference locally for **five models**, first on a labelled smoke
test and then on E3 (closed-question challenges) and E4 (open-response challenges).
Phase A collects each model's own first answer. The included builder uses that
answer to construct Phase B. Run Phase B with the same model and configuration.
No model weights are included. No hosted-model reruns are assigned to you.

**Generate Phase B with the included script, but do not score the round-two
responses. Send the raw responses, the Phase B manifests and the provenance file.**
We score all **fifteen models** centrally with one comparator. Constructing
challenges is not final evaluation scoring. Only the smoke test is scored locally.

Keep this bundle unchanged. It intentionally includes private construction
answers; it is a developer handoff, not an answer-free benchmark release.

| Model / exact checkpoint | Smoke questions | E3 Phase A | E4 Phase A |
| --- | ---: | ---: | ---: |
| Qwen3-VL-8B-Instruct / `Qwen/Qwen3-VL-8B-Instruct` | 847 | 3,400 | 2,000 |
| Qwen3-VL-8B-Thinking / `Qwen/Qwen3-VL-8B-Thinking` | 847 | 3,400 | 2,000 |
| Molmo2-8B / `allenai/Molmo2-8B` | 847 | 3,400 | 2,000 |
| InternVL3.5-8B / `OpenGVLab/InternVL3_5-8B` | 847 | 3,400 | 2,000 |
| DeepSeek-VL2-Small / `deepseek-ai/deepseek-vl2-small` | 847 | 3,400 | 2,000 |

E3 and E4 share 15 images: **2,665 unique evaluation images**, copied byte-for-byte
from the hosted inputs. The 179 fresh smoke images are separate. Phase B row
counts depend on actual Phase A replies; use the generated integrity sidecars,
not a guessed fixed count. No extra E1 inference is requested.

## 2. Hardware and software

These commands target Linux with Bash, NVIDIA CUDA GPUs, Python **3.12**, a working
NVIDIA driver, `curl`, and two terminals. Native Windows serving is not the
reference workflow; use a Linux GPU host. Install Python 3.12 and its venv support
before starting. Keep ample disk space for five unquantized model snapshots,
environments and outputs (budget roughly 200 GB; this is a planning allowance,
not a measured requirement). Downloading weights needs Internet; inference is
restricted to a credential-free loopback endpoint.

Serve **one model at a time**. An 80 GB GPU is a practical starting point, not a
tested minimum or a guarantee. Approximately 8B BF16 weights alone are around
16 GB before the vision tower, caches and runtime overhead. DeepSeek's activated
parameter count is not its full resident weight size. A 24 GB GPU may run out of
memory. Keep BF16 and avoid quantization/model substitutions. If necessary, use
two compatible GPUs and add `--tensor-parallel-size 2`; record this before smoke
testing and keep it fixed. An unsupported kernel or out-of-memory error is a
setup failure, not a result: do not skip that model or silently resize images.

**Qwen3-VL-8B-Thinking can generate long reasoning traces and take far longer**
than an instruct model. Only one of these five checkpoints is explicitly named
Thinking. Do not assume a second thinking checkpoint or substitute a different
variant. Other models may also generate long replies. Never shorten responses
after generation. Watch timeout and truncation diagnostics, not just parse rate.

The serving recipe below uses vLLM 0.28.0, whose
[supported-model list](https://docs.vllm.ai/en/v0.28.0/models/supported_models/)
includes the five model families. These launch instructions were checked against
documentation, **not hardware-tested in this handoff**. Checkpoint-specific
references: [Qwen](https://huggingface.co/Qwen/Qwen3-VL-8B-Thinking),
[Molmo2](https://huggingface.co/allenai/Molmo2-8B),
[InternVL](https://huggingface.co/OpenGVLab/InternVL3_5-8B),
[DeepSeek](https://huggingface.co/deepseek-ai/deepseek-vl2-small), and
[vLLM serving options](https://docs.vllm.ai/en/v0.28.0/cli/serve/).
Model licences remain those of their publishers, separately from this bundle.

## 3. Prepare the two environments and immutable model snapshots

Extract the ZIP into a directory named `grip-handoff`. Open Terminal A inside that
directory; every command below assumes that current directory. Work products go
into sibling `../work`, not inside the immutable handoff.

```bash
python3.12 -m venv .venv-score
.venv-score/bin/python -m pip install -r requirements-scoring.lock.txt
.venv-score/bin/python -B verify.py --integrity-only
.venv-score/bin/python -B build_phase_b.py --help
mkdir -p ../work/configs ../work/responses ../work/smoke ../work/phase_b ../work/logs
.venv-score/bin/python -m pip freeze > ../work/environment.txt
nvidia-smi > ../work/hardware.txt

python3.12 -m venv .venv-server
.venv-server/bin/python -m pip install 'vllm==0.28.0'
.venv-server/bin/python -m pip freeze > ../work/server_environment.txt
.venv-server/bin/python prepare_models.py --output-dir ../work/models --record ../work/checkpoint_revisions.json
```

`prepare_models.py` resolves and records one immutable repository commit per
checkpoint, then downloads that exact snapshot. Keep the snapshots and revision
file; do not download a newer revision between rounds or after approval. The
download helper calls Hugging Face only on your machine when you run it, not as
part of inference. No access token or credential belongs in the return archive.
If interrupted before the revision file is written, rerun this preparation step
before any smoke/evaluation run, then keep the resulting record fixed.

Do not edit scoring libraries to work around an installation error. Phase B
requires Python 3.12, NumPy 2.2.3 and Pandas 3.0.5 exactly. Scorer, tolerance
configuration, vendored dependencies and construction inputs are pinned by
SHA-256. A mismatch causes an unconditional refusal; no override flag exists.

## 4. Start the correct model server (Terminal B)

In Terminal B, also enter `grip-handoff`. Run **one** of the following commands,
matching the model you will run in Terminal A. Leave it running until that model
finishes. Stop it with Ctrl-C before selecting the next model; port 8000 must not
be shared by two servers. Original checkpoint preprocessing/chat templates are
used. `--trust-remote-code` allows publisher code in the downloaded snapshot;
use only the checkpoint sources listed above.

```bash
# Qwen3-VL-8B-Instruct
.venv-server/bin/vllm serve ../work/models/Qwen3-VL-8B-Instruct --served-model-name Qwen3-VL-8B-Instruct --host 127.0.0.1 --port 8000 --dtype bfloat16 --trust-remote-code --max-num-seqs 1 --generation-config vllm --seed 0

# Qwen3-VL-8B-Thinking
.venv-server/bin/vllm serve ../work/models/Qwen3-VL-8B-Thinking --served-model-name Qwen3-VL-8B-Thinking --host 127.0.0.1 --port 8000 --dtype bfloat16 --trust-remote-code --max-num-seqs 1 --generation-config vllm --seed 0

# Molmo2-8B
.venv-server/bin/vllm serve ../work/models/Molmo2-8B --served-model-name Molmo2-8B --host 127.0.0.1 --port 8000 --dtype bfloat16 --trust-remote-code --max-num-seqs 1 --generation-config vllm --seed 0

# InternVL3.5-8B
.venv-server/bin/vllm serve ../work/models/InternVL3.5-8B --served-model-name InternVL3.5-8B --host 127.0.0.1 --port 8000 --dtype bfloat16 --trust-remote-code --max-num-seqs 1 --generation-config vllm --seed 0

# DeepSeek-VL2-Small
.venv-server/bin/vllm serve ../work/models/DeepSeek-VL2-Small --served-model-name DeepSeek-VL2-Small --host 127.0.0.1 --port 8000 --dtype bfloat16 --trust-remote-code --max-num-seqs 1 --generation-config vllm --seed 0
```

Wait for the server's startup-complete message. In Terminal A check readiness and
confirm that the returned model ID matches your chosen alias:

```bash
curl --fail http://127.0.0.1:8000/v1/models
```

Do not enable a reasoning parser that removes reasoning from `message.content`.
The runner preserves exactly that text field; it does not combine a separate
`reasoning_content` field with it. The server must return a single content string
and `finish_reason`. Confirm actual image use with smoke accuracy, not merely
that this readiness check works. Retain server-version and launch-setting notes
in `../work/server_environment.txt` if you change the documented setup.

## 5. Run and score smoke tests, for each of the five models

In Terminal A set `MODEL` to match Terminal B. First run the following block with
the first assignment. Repeat the whole block with each of the other four names
after restarting Terminal B with its matching command:

```bash
MODEL=Qwen3-VL-8B-Instruct
# Subsequent smoke passes: use exactly one of these assignments instead:
# MODEL=Qwen3-VL-8B-Thinking
# MODEL=Molmo2-8B
# MODEL=InternVL3.5-8B
# MODEL=DeepSeek-VL2-Small

.venv-score/bin/python -B workflow.py init-config --model "$MODEL" --output "../work/configs/$MODEL.json"
.venv-score/bin/python -u -B run_local.py --manifest smoketest/manifest.csv --model "$MODEL" --config "../work/configs/$MODEL.json" --output "../work/responses/${MODEL}_SMOKE.jsonl"
.venv-score/bin/python -B verify.py --manifest smoketest/manifest.csv --responses "../work/responses/${MODEL}_SMOKE.jsonl" --model "$MODEL" --experiment SMOKE
set -o pipefail
.venv-score/bin/python -B smoketest/score_smoke.py --responses "../work/responses/${MODEL}_SMOKE.jsonl" --model "$MODEL" | tee "../work/smoke/${MODEL}_scores.txt"
```

Do not rerun `init-config` on resume: it refuses to overwrite an existing config.
The generated recipe is **proposed for smoke, not recovered historical settings**:
greedy temperature 0, top-p 1, max output 2,048 tokens (8,192 for Thinking), no
extra system message/reasoning override, original images, existing 120-second
request timeout and retry policy. Historical open-weight decoding, quantization,
hardware, stack and run dates were not recorded. Hosted source defaults are
listed in `config.json`; provider effective defaults/CLI overrides were not
recorded. Do not claim that the new recipe reproduces undocumented settings.

Smoke coverage is **179 fresh images / 847 questions / 30 domains**, not the
originally requested 204 / 1,020 / 34. At the requested out-of-range indices the
three nested generators and surface_topology fail; RPM has only five accepted
images; eight generators lack fifth-question retrofits. Details are in
`smoketest/STATUS.json`. No released image, replacement seed or invented question
was used to conceal these gaps. These smoke IDs do not overlap evaluation or the
released index. Only the smoke scorer reads `private/smoke_answers.jsonl`.

Read per-domain smoke accuracy AND parse rate. Compare with
`smoketest/hosted_reference.csv`: hosted-tier min/max values are reference points
on different images and their original scorer, **not pass thresholds or targets**.
A high extraction rate with uniformly implausible accuracy can indicate a broken
image pipeline. Zero/error-heavy responses, repeated generic text, length
truncations and timeouts must be resolved before full inference. Never invent
missing answers. There is no measured runtime for this handoff: use elapsed
smoke time / 847 to estimate seconds per query, then multiply by the workload.
There are 27,000 Phase A queries over five models; Phase B totals come from its
generated manifests. Thinking may dominate total time. Budget days, not an
unverified hours estimate, until you measure throughput.

### Mandatory approval gate — STOP here

Send the five `../work/smoke/*_scores.txt` files, smoke raw JSONLs, verification
results, resolved configs, checkpoint revisions and environment/hardware records
back to the person who sent you this ZIP, using the same delivery channel.
**WAIT for their explicit reply approving the smoke results, available smoke
coverage and decoding recipe before starting any full run.** No additional
contact person or address is required or included. Do not self-approve.

After that reply, record its real text/date in the command below. Replace the
quoted note with the approval you actually received; do not run this command
before approval. It changes only approval bookkeeping, not generation settings.

```bash
for MODEL in Qwen3-VL-8B-Instruct Qwen3-VL-8B-Thinking Molmo2-8B InternVL3.5-8B DeepSeek-VL2-Small; do
  .venv-score/bin/python -B workflow.py approve --config "../work/configs/$MODEL.json" --approval-note 'REPLACE with the explicit approval received and its date' || break
done
```

If a smoke setting needs changing, agree it before full inference, use a new
output/work directory, and rerun smoke. Do not mix responses from different
settings in one result file. Image truncation/context overflow is not permission
to crop images or truncate conversation history. Full runs are blocked by the
runner until an approval record exists.

## 6. Phase A, then construct and run Phase B

For **each model**, restart its server as in section 4, set `MODEL` to the exact
matching name, then run this entire block. It runs both experiments in order and
stops on the first failed verification/build/run. Repeat for all five names from
the model table, using their already-approved configurations.

```bash
MODEL=Qwen3-VL-8B-Instruct
# On subsequent passes replace the assignment with each other exact model name.
set -e
set -o pipefail
for EXP in E3 E4; do
  .venv-score/bin/python -u -B run_local.py --manifest "evaluation/${EXP}_phase_a.csv" --model "$MODEL" --config "../work/configs/$MODEL.json" --output "../work/responses/${MODEL}_${EXP}_A.jsonl"
  .venv-score/bin/python -B verify.py --manifest "evaluation/${EXP}_phase_a.csv" --responses "../work/responses/${MODEL}_${EXP}_A.jsonl" --model "$MODEL" --experiment "$EXP"
  .venv-score/bin/python -B build_phase_b.py --experiment "$EXP" --model "$MODEL" --responses "../work/responses/${MODEL}_${EXP}_A.jsonl" --output-dir ../work/phase_b
  .venv-score/bin/python -u -B run_local.py --manifest "../work/phase_b/${MODEL}_${EXP}_phase_b.csv" --phase-b-integrity "../work/phase_b/${MODEL}_${EXP}_phase_b.integrity.json" --round1-manifest "evaluation/${EXP}_phase_a.csv" --round1-responses "../work/responses/${MODEL}_${EXP}_A.jsonl" --model "$MODEL" --config "../work/configs/$MODEL.json" --output "../work/responses/${MODEL}_${EXP}_B.jsonl"
  .venv-score/bin/python -B verify.py --manifest "../work/phase_b/${MODEL}_${EXP}_phase_b.csv" --phase-b-integrity "../work/phase_b/${MODEL}_${EXP}_phase_b.integrity.json" --responses "../work/responses/${MODEL}_${EXP}_B.jsonl" --model "$MODEL" --experiment "$EXP"
done
```

Only one builder process may write `../work/phase_b` at a time. Build once per
model/experiment and keep every CSV, integrity sidecar and provenance file. Do
not overwrite a successfully built Phase B when resuming inference. If a build
was interrupted, preserve its partial files and build to a fresh output directory;
do not hand-edit or merge provenance. Before the full return, retain a single
complete, consistent directory with all ten model/experiment entries. If this
requires recovery, send the partial build evidence back rather than guessing.

The builder scores Round 1 solely to assign challenges with the pinned
construction comparators: E3's frozen legacy strict comparator and E4's approved
acceptance-set helper. Final tolerance-aware outcome scoring remains central.
The tolerance configuration also records the smoke scorer's zero-relative
fallback 0.01 and symmetry moduli (90/60/120 degrees).

E4's hard-coded `DEFAULT_HOSTED_PANEL` in `build_phase_b.py` is:
`gpt_5_6_luna`, `claude_opus_5`, `claude_sonnet_5`, `gemini_3_8_flash`,
`grok_4_6`, `inking`, `muse_glimmer_30b`. For each target, the panel is those seven
plus that one open-weight target. Three natural peers are selected excluding the
target, so shown peers are always from the same seven hosted models. Other
open-weight models are never inserted. Missing selected peer replies cause a
recorded omission, not a replacement. Assertions enforce this policy. The
separate central hosted constructed-consensus rerun is not included here.

Phase B manifests contain only `row_id,model,image_path,prompt_text`. Paths are
relative `images/<domain>/<image_id>.png`; absolute paths/drive letters fail.
Asserted answers occur only as model-facing prose. The runner restores the exact
first question, image and the model's own unmodified first reply, then adds the
second user prompt. It never reads `private/`; an OS file-open guard rejects such
reads, including traversal/aliases. Only the builder and smoke scorer use answers.

Each successful build updates `phase_b_provenance.json`: scorer/config/input
hashes, Python/library versions, Round-1 correct/incorrect/unparseable counts,
per-arm counts and every produced manifest's SHA-256. Return it unedited. We
independently regenerate Phase B from your raw Round-1 files and byte-compare
manifests. **Any difference means construction drift and rejection.**

## 7. Check progress, interrupt safely and resume

The runner prints progress every 25 rows and checkpoints each completed request.
Keep the terminal output (or redirect it into `../work/logs`). In another terminal:

```bash
MODEL=Qwen3-VL-8B-Instruct
.venv-score/bin/python -B workflow.py progress --output "../work/responses/${MODEL}_E3_A.jsonl"
# Change the suffix to SMOKE, E4_A, E3_B or E4_B for the run being monitored.
nvidia-smi
```

Ctrl-C stops inference. Keep the hidden `.progress_<output filename>` directory
under `../work/responses`; it contains the per-row cache. Restart the same server
and rerun the **identical run_local.py command**, with the same output path,
model, manifests, config and Round-1 files. Usable cached replies are skipped;
failed/empty replies and literal none/null replies are retried according to the
existing resume policy. Config/input fingerprints prevent incompatible resume.
Cache records and final JSONLs are written by atomic replacement. The final
JSONL appears only after the pass completes; absence during progress is normal.
Do not delete caches or change settings to force a resume. Do not reinitialize
configs or rebuild an already-issued Phase B. Run the corresponding `verify.py`
command again after completion. Do not rerun successful truncated replies in
place with a different budget; retain evidence and get a revised run approved.

Requests retry HTTP 429, HTTP >=500, connection failures and timeouts up to
**five additional times (six outer attempts)**, 120 seconds each by default.
Backoff is 1, 2, 4, 8, 16 seconds plus uniform jitter up to min(1 second, 10% of
the delay). Other errors fail immediately. Empty successful content is recorded
as-is without immediate semantic retry. Missing images cause no request. There
is no SDK retry layer; server-internal retries/defaults must be recorded if any.

## 8. Verify the complete delivery and package it

After all five models finish, the following command validates all **25 runs**
(five smoke, ten Phase A, ten Phase B), expected counts, exact IDs, schemas,
duplicates, nonempty responses, errors, Phase B hashes and ten provenance entries:

```bash
.venv-score/bin/python -B workflow.py verify-return --work-dir ../work
.venv-score/bin/python -B workflow.py pack-return --work-dir ../work --output ../GRIP_five_model_raw_return.zip
```

Both commands save `../work/verify_output.json`. Missing/incomplete runs fail;
packaging refuses them. Read every run's `complete`, error count, ANSWER-label
extraction rate, truncation count and unknown finish reasons. Extraction is a
format diagnostic, not accuracy. Truncations are retained/reported rather than
silently removed; discuss their acceptability at the gate. The return packer
includes an explicit allowlist, not your whole work directory.

Send **`GRIP_five_model_raw_return.zip`** back through the same channel used to
receive this handoff. It contains:

- `responses/`: all 25 verbatim raw JSONLs, including smoke, Phase A and Phase B.
- `phase_b/`: ten generated CSVs, ten integrity sidecars and the cumulative
  `phase_b_provenance.json`.
- `smoke/`: five per-domain smoke score reports.
- `configs/`: five resolved approved run configs; `verify_output.json` at root.
- `environment.txt`, `server_environment.txt`, `hardware.txt` and
  `checkpoint_revisions.json` for reproducibility.

Never return weights, `.env`, credentials, private answer tables or progress
caches. Inspect environment/approval notes for secrets before sending. Keep all
original work files until central acceptance. Do not score Round 2 or send
locally computed final accuracy tables.

Raw records contain exactly these six fields; `response_raw` is the verbatim
server output, including whitespace, not parsed/trimmed/postprocessed text:

```json
{"row_id":"E3:example:example_0000_q1","model":"Qwen3-VL-8B-Instruct","response_raw":"  ANSWER: <verbatim text>\n","error":null,"finish_reason":"stop","timestamp":"2026-11-08T00:00:00+00:00"}
```

## 9. Bundle map and failure checklist

```text
README.md                       This complete guide
config.json                     Immutable hosted defaults / inference template
INTEGRITY.json                  File SHA-256 inventory and expected model counts
requirements-scoring.lock.txt   Exact construction/scoring libraries
run_local.py                    Both E3/E4, both rounds; no answer access
build_phase_b.py                Pinned challenge construction and provenance
verify.py                       Answer-free integrity/completeness checks
workflow.py                     Config, smoke gate, progress, return verification/ZIP
prepare_models.py               Recipient-side immutable weight downloads
compare_phase_b.py              Central byte-diff acceptance utility
LICENSE                         Bundle licence
evaluation/                     Two Phase A manifests and 2,665 stored images
private/                        ANSWERS, construction inputs and smoke labels/scenes
scoring/                        Pinned code/config/vendor source; no item answer tables
smoketest/                      Fresh images, prompt manifest, diagnostic scorer/references
```

Only `private/` holds per-item answers/scenes. Evaluation manifests have no answer
fields. Do not change prompts, response-format suffixes (already embedded), image
pixels, model identity/revision, approved decoding, dtype, chat templates or image
preprocessing between smoke and evaluation. The runner transmits original PNG
bytes, image before text, no extra system prompt and no resize/detail override;
the model's native image processor is part of the recorded serving stack.

If integrity/pins fail, restore the issued bundle—never bypass checks. If the
model alias is wrong, restart the correct server. If inference errors remain,
resume the identical command; do not remove rows. If Phase B refuses incomplete
Round 1, fix/retry Round 1 first. If context limits, timeout, library compatibility
or smoke results remain unresolved, stop and return the exact error and evidence
to the sender through the existing channel. No guide can authorize inventing
answers or changing the protocol to get past a failure.

# Open-weight raw-response gap

The repository has complete Test-1 JSONL responses for the ten models in the typed report and **no complete or partial open-weight Test-1 response artefacts**. Aggregate values cannot be repaired without raw responses. Any table combining these ten repaired scores with six unrepaired open-weight scores is therefore invalid.

## Required export

Each missing model needs a Test-1-compatible JSONL export containing one latest successful record for every row of:

`tests/test_1_closed_loop/plan/closed_loop_manifest.csv`

Required fields per line:

- `row_id` — exact manifest key (8,500 unique rows per model)
- `model` — stable model key
- `response_raw` — verbatim stored answer
- `error` — null/empty on success, otherwise the recorded failure

Strongly recommended provenance fields are `domain`, `stem`, `question_id`, `level`, `image_path`, `prompt_sent`, token counts, latency, timestamp, provider, and exact model ID. The scorer keys by `row_id`; aggregates alone are insufficient.

## Where the local runner writes

`GRIP_Model_Evaluation.ipynb` defines the local/open-weight cache as:

`eval_results/<model_key>/<domain>.jsonl`

and the later protocol cache as:

`eval_results_protocol/<test_name>/<model_key>/<domain>.jsonl`.

Those directories are not present in this repository. If they still exist on the machine/session used for local inference, the per-domain files must be exported and merged into one Test-1-compatible response set per model. The notebook registry lists ten possible open-weight candidates, but this repository does not contain a frozen record identifying which six were selected for the paper; that mapping must come from the local-run configuration or manuscript source rather than being guessed.

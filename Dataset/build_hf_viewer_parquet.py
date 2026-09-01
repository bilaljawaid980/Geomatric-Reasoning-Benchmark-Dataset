"""Build sharded, image-embedded Parquet views for the Hugging Face viewer."""
from __future__ import annotations

import csv
import json
import math
from collections import OrderedDict, defaultdict
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
from datasets import Features, Image, Value

REPO = Path(__file__).resolve().parents[1]
DATASETS = REPO / "Dataset"
COMBINED = REPO / "combined"
ANSWERS_CSV = COMBINED / "all_answers_combined.csv"
REPORT = DATASETS / "hf_viewer_parquet_report.json"
TARGET_SHARD_MIB = 470
BATCH_ROWS = 500


def read_csv_rows(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        yield from csv.DictReader(handle)


def image_partitions() -> tuple[dict[str, int], list[int]]:
    unique: list[tuple[str, int]] = []
    seen = set()
    for row in read_csv_rows(ANSWERS_CSV):
        rel = row["image_path"]
        if rel in seen:
            continue
        seen.add(rel)
        path = REPO / rel
        if not path.is_file():
            raise FileNotFoundError(path)
        unique.append((rel, path.stat().st_size))
    if len(unique) != 100_000:
        raise RuntimeError(f"Expected 100,000 unique images, found {len(unique)}")
    total = sum(size for _, size in unique)
    shard_count = max(1, round(total / (TARGET_SHARD_MIB * 2**20)))
    target = total / shard_count
    mapping: dict[str, int] = {}
    totals = [0] * shard_count
    shard = 0
    cumulative = 0
    for rel, size in unique:
        if shard < shard_count - 1 and cumulative >= target * (shard + 1):
            shard += 1
        mapping[rel] = shard
        totals[shard] += size
        cumulative += size
    return mapping, totals


def output_path(stem: str, shard: int, total: int) -> Path:
    return COMBINED / f"{stem}-{shard:05d}-of-{total:05d}.parquet"


def clear_outputs(stem: str) -> None:
    for path in COMBINED.glob(f"{stem}-*-of-*.parquet"):
        path.unlink()
    for path in COMBINED.glob(f".{stem}-*.tmp"):
        path.unlink()


def write_batches(stem: str, schema: pa.Schema, rows, shard_count: int) -> tuple[int, list[Path]]:
    clear_outputs(stem)
    writers: dict[int, pq.ParquetWriter] = {}
    buffers: dict[int, list[dict]] = defaultdict(list)
    temp_paths: dict[int, Path] = {}
    count = 0

    def flush(shard: int) -> None:
        batch = buffers[shard]
        if not batch:
            return
        if shard not in writers:
            temp = COMBINED / f".{stem}-{shard:05d}.tmp"
            temp_paths[shard] = temp
            writers[shard] = pq.ParquetWriter(
                temp, schema, compression="zstd", compression_level=9,
                use_dictionary=True, write_statistics=True,
            )
        table = pa.Table.from_pylist(batch, schema=schema)
        writers[shard].write_table(table, row_group_size=len(batch))
        batch.clear()

    for shard, row in rows:
        buffers[shard].append(row)
        count += 1
        if len(buffers[shard]) >= BATCH_ROWS:
            flush(shard)
    for shard in range(shard_count):
        flush(shard)
    for writer in writers.values():
        writer.close()
    if set(writers) != set(range(shard_count)):
        raise RuntimeError(f"Empty Parquet shard: produced {sorted(writers)}")
    final_paths = []
    for shard in range(shard_count):
        final = output_path(stem, shard, shard_count)
        temp_paths[shard].replace(final)
        final_paths.append(final)
    return count, final_paths


def answer_rows(mapping: dict[str, int]):
    last_rel = None
    image_bytes = None
    for source in read_csv_rows(ANSWERS_CSV):
        rel = source["image_path"]
        if rel != last_rel:
            image_bytes = (REPO / rel).read_bytes()
            last_rel = rel
        yield mapping[rel], {
            "dataset": source["dataset"],
            "dataset_version": source["dataset_version"],
            "question_id": source["question_id"],
            "task": source["task"],
            "image": source["image"],
            "image_bytes": {"bytes": image_bytes, "path": None},
            "image_path": source["image_path"],
            "prompt": source["prompt"],
            "groundtruth": source["groundtruth"],
            "answer_format": source["answer_format"],
        }


def annotation_sources():
    manifests = sorted(DATASETS.glob("*/build_manifest.json"))
    if len(manifests) != 34:
        raise RuntimeError(f"Expected 34 dataset manifests, found {len(manifests)}")
    for manifest in manifests:
        folder = manifest.parent
        annotations = folder / "annotations.jsonl"
        if not annotations.is_file():
            raise FileNotFoundError(annotations)
        manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
        manifest_version = str(manifest_data["dataset_version"])
        dataset = folder.name.rsplit("_dataset_", 1)[0]
        for line in annotations.read_text(encoding="utf-8").splitlines():
            if line:
                yield dataset, folder, manifest_version, json.loads(line)


def value_kind(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    if isinstance(value, str):
        return "string"
    return "json"


def annotation_types() -> OrderedDict[str, str]:
    kinds: dict[str, set[str]] = defaultdict(set)
    for _, _, _, row in annotation_sources():
        for key, value in row.items():
            if key in {"id", "dataset_version", "image_path"}:
                continue
            kind = value_kind(value)
            if kind:
                kinds[key].add(kind)
    result: OrderedDict[str, str] = OrderedDict()
    for key in sorted(kinds):
        seen = kinds[key]
        if seen <= {"bool"}:
            result[key] = "bool"
        elif seen <= {"int"}:
            result[key] = "int"
        elif seen <= {"int", "float"}:
            result[key] = "float"
        elif seen <= {"string"}:
            result[key] = "string"
        else:
            result[key] = "json"
    return result


def normalize(value, kind: str):
    if value is None:
        return None
    if kind == "bool":
        return bool(value)
    if kind == "int":
        return int(value)
    if kind == "float":
        return float(value)
    if kind == "string":
        return str(value)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def annotation_rows(mapping: dict[str, int], types: OrderedDict[str, str]):
    for dataset, folder, manifest_version, source in annotation_sources():
        rel = (Path("Dataset") / folder.name / source["image_path"]).as_posix()
        if rel not in mapping:
            raise RuntimeError(f"Annotation image is absent from combined questions: {rel}")
        row = {
            "dataset": dataset,
            "dataset_version": str(source.get("dataset_version") or manifest_version),
            "id": str(source["id"]),
            "image": {"bytes": (REPO / rel).read_bytes(), "path": None},
            "image_filename": Path(source["image_path"]).name,
            "image_path": source["image_path"],
        }
        for key, kind in types.items():
            row[key] = normalize(source.get(key), kind)
        yield mapping[rel], row


def shard_stats(paths: list[Path]) -> list[dict]:
    result = []
    for path in paths:
        parquet = pq.ParquetFile(path)
        result.append({
            "file": path.name,
            "bytes": path.stat().st_size,
            "mib": path.stat().st_size / 2**20,
            "rows": parquet.metadata.num_rows,
            "row_groups": parquet.metadata.num_row_groups,
        })
    return result


def main() -> None:
    mapping, unique_payloads = image_partitions()
    shard_count = len(unique_payloads)
    answer_features = Features(OrderedDict([
        ("dataset", Value("string")), ("dataset_version", Value("string")),
        ("question_id", Value("string")), ("task", Value("string")),
        ("image", Value("string")), ("image_bytes", Image()),
        ("image_path", Value("string")),
        ("prompt", Value("string")), ("groundtruth", Value("string")),
        ("answer_format", Value("string")),
    ]))
    answer_count, answer_paths = write_batches(
        "all_answers_combined", answer_features.arrow_schema,
        answer_rows(mapping), shard_count,
    )
    if answer_count != 500_000:
        raise RuntimeError(f"Expected 500,000 answer rows, wrote {answer_count}")

    types = annotation_types()
    annotation_feature_map = OrderedDict([
        ("dataset", Value("string")), ("dataset_version", Value("string")),
        ("id", Value("string")), ("image", Image()),
        ("image_filename", Value("string")), ("image_path", Value("string")),
    ])
    for key, kind in types.items():
        annotation_feature_map[key] = Value({"bool": "bool", "int": "int64", "float": "float64"}.get(kind, "string"))
    annotation_features = Features(annotation_feature_map)
    annotation_count, annotation_paths = write_batches(
        "all_annotations_combined", annotation_features.arrow_schema,
        annotation_rows(mapping, types), shard_count,
    )
    if annotation_count != 100_000:
        raise RuntimeError(f"Expected 100,000 annotation rows, wrote {annotation_count}")

    answer_stats = shard_stats(answer_paths)
    annotation_stats = shard_stats(annotation_paths)
    report = {
        "logical_rows": {"default_answers": answer_count, "annotations": annotation_count},
        "raw_png_payload": {
            "unique_bytes": sum(unique_payloads),
            "unique_gib": sum(unique_payloads) / 2**30,
            "fivefold_logical_bytes": sum(unique_payloads) * 5,
            "fivefold_logical_gib": sum(unique_payloads) * 5 / 2**30,
        },
        "compression": "zstd level 9; five adjacent question rows contain identical embedded PNG bytes",
        "shard_count_per_config": shard_count,
        "unique_png_payload_mib_by_shard": [value / 2**20 for value in unique_payloads],
        "default_answer_shards": answer_stats,
        "annotation_shards": annotation_stats,
        "default_total_gib": sum(item["bytes"] for item in answer_stats) / 2**30,
        "annotations_total_gib": sum(item["bytes"] for item in annotation_stats) / 2**30,
        "annotation_metadata_columns": list(annotation_feature_map),
        "annotation_complex_columns_encoded_as_json": [key for key, kind in types.items() if kind == "json"],
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

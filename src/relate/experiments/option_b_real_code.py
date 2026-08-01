"""Option B: real frozen-code representation premise test.

The canonical scientific decision is frozen in
``docs/experiments/08-option-b-real-code-premise-test.md``.
This module implements that contract without changing its thresholds.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import platform
import sys
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score

MODEL_ID = "microsoft/codebert-base"
PRIMITIVES = ("cyclomatic_complexity", "max_control_depth", "distinct_call_sites")
ALPHAS = (0.01, 0.1, 1.0, 10.0, 100.0)
MANIFEST_SEED = 8112026
AST_RECURSION_LIMIT = 1_000


@dataclass(frozen=True)
class OptionBConfig:
    train_limit: int = 20_000
    validation_limit: int = 4_000
    test_limit: int = 4_000
    min_tokens: int = 32
    max_tokens: int = 256
    max_pairs_per_query: int = 128
    min_rank_separation: int = 5
    max_rank_separation: int = 25
    ridge_alphas: tuple[float, ...] = ALPHAS
    continuation_gap: float = 0.10
    bootstrap_repetitions: int = 2_000


@dataclass(frozen=True)
class FunctionRecord:
    split: str
    repository: str
    path: str
    function_id: str
    code: str
    code_sha256: str
    normalized_ast_sha256: str
    token_count: int
    cyclomatic_complexity: float
    max_control_depth: float
    distinct_call_sites: float

    @property
    def stable_key(self) -> str:
        value = "\n".join((self.repository, self.path, self.function_id, self.code_sha256)).encode()
        return hashlib.sha256(value).hexdigest()

    @property
    def primitive_vector(self) -> np.ndarray:
        return np.asarray(
            (
                self.cyclomatic_complexity,
                self.max_control_depth,
                self.distinct_call_sites,
            ),
            dtype=np.float64,
        )


class _PrimitiveVisitor(ast.NodeVisitor):
    """Extract the three frozen AST primitives.

    Nested functions, lambdas and classes are intentionally excluded from the
    enclosing function's statistics.
    """

    def __init__(self) -> None:
        self.complexity = 1
        self.depth = 0
        self.max_depth = 0
        self.calls: set[str] = set()
        self._root_seen = False

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if self._root_seen:
            return
        self._root_seen = True
        for statement in node.body:
            self.visit(statement)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if self._root_seen:
            return
        self._root_seen = True
        for statement in node.body:
            self.visit(statement)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        return

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return

    def visit_If(self, node: ast.If) -> None:
        self._visit_if_chain(node, enter_depth=True)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.complexity += 1
        self._visit_control(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.complexity += 1
        self._visit_control(node)

    def visit_While(self, node: ast.While) -> None:
        self.complexity += 1
        self._visit_control(node)

    def visit_Try(self, node: ast.Try) -> None:
        self._visit_control(node)

    def visit_With(self, node: ast.With) -> None:
        self._visit_control(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self._visit_control(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.complexity += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        # A chained expression with n values contributes n-1 decisions.
        self.complexity += max(len(node.values) - 1, 0)
        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension_expression(node.generators, (node.elt,))

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comprehension_expression(node.generators, (node.elt,))

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comprehension_expression(node.generators, (node.key, node.value))

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_comprehension_expression(node.generators, (node.elt,))

    def visit_Match(self, node: ast.Match) -> None:
        # The first case is the base path; each additional case adds a branch.
        self.complexity += max(len(node.cases) - 1, 0)
        self._visit_control(node)

    def visit_Call(self, node: ast.Call) -> None:
        self.calls.add(_normalize_call_target(node.func))
        self.generic_visit(node)

    def _visit_if_chain(self, node: ast.If, *, enter_depth: bool) -> None:
        self.complexity += 1
        if enter_depth:
            self._enter_control()
        self.visit(node.test)
        for statement in node.body:
            self.visit(statement)
        if self._has_elif(node):
            self._visit_if_chain(node.orelse[0], enter_depth=False)
        else:
            for statement in node.orelse:
                self.visit(statement)
        if enter_depth:
            self.depth -= 1

    @staticmethod
    def _has_elif(node: ast.If) -> bool:
        return (
            len(node.orelse) == 1
            and isinstance(node.orelse[0], ast.If)
            and node.orelse[0].col_offset == node.col_offset
        )

    def _visit_comprehension_expression(
        self,
        generators: list[ast.comprehension],
        result_nodes: tuple[ast.AST, ...],
    ) -> None:
        entered = 0
        for generator in generators:
            # Every generator is a loop decision; every filter is an additional decision.
            self.complexity += 1 + len(generator.ifs)
            self.visit(generator.iter)
            self._enter_control()
            entered += 1
            self.visit(generator.target)
            for condition in generator.ifs:
                self.visit(condition)
        for result_node in result_nodes:
            self.visit(result_node)
        self.depth -= entered

    def _enter_control(self) -> None:
        self.depth += 1
        self.max_depth = max(self.max_depth, self.depth)

    def _visit_control(self, node: ast.AST) -> None:
        self._enter_control()
        self.generic_visit(node)
        self.depth -= 1


def pin_ast_recursion_limit() -> None:
    """Set the recursion limit used by canonical primitive extraction."""

    if sys.getrecursionlimit() != AST_RECURSION_LIMIT:
        sys.setrecursionlimit(AST_RECURSION_LIMIT)


def _normalize_call_target(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return "<dynamic>"


def normalize_ast(tree: ast.AST) -> str:
    return ast.dump(tree, annotate_fields=True, include_attributes=False)


def extract_primitives(code: str) -> tuple[str, np.ndarray]:
    tree = ast.parse(code)
    top_level = [
        node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    if len(top_level) != 1:
        raise ValueError("sample must contain exactly one top-level function")
    visitor = _PrimitiveVisitor()
    visitor.visit(top_level[0])
    normalized = normalize_ast(tree)
    values = np.asarray(
        (visitor.complexity, visitor.max_depth, len(visitor.calls)), dtype=np.float64
    )
    return hashlib.sha256(normalized.encode()).hexdigest(), values


def iter_jsonl(paths: Iterable[Path], split: str) -> Iterator[dict[str, Any]]:
    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                row = json.loads(line)
                row["_source_file"] = str(path)
                row["_source_line"] = line_number
                row["_split"] = split
                yield row


def _field(row: dict[str, Any], *names: str, default: str = "") -> str:
    for name in names:
        value = row.get(name)
        if value is not None:
            return str(value)
    return default


def build_records(
    rows: Iterable[dict[str, Any]],
    tokenizer: Any,
    config: OptionBConfig,
) -> tuple[list[FunctionRecord], Counter[str]]:
    pin_ast_recursion_limit()
    records: list[FunctionRecord] = []
    reasons: Counter[str] = Counter()
    for row in rows:
        code = _field(row, "code", "whole_func_string", "original_string", "func_code_string")
        if not code:
            reasons["missing_code"] += 1
            continue
        try:
            ast_sha, primitive = extract_primitives(code)
        except RecursionError:
            reasons["ast_recursion_limit"] += 1
            continue
        except (SyntaxError, ValueError):
            reasons["ast_ineligible"] += 1
            continue
        token_count = len(tokenizer(code, add_special_tokens=True, truncation=False)["input_ids"])
        if token_count < config.min_tokens or token_count > config.max_tokens:
            reasons["token_length"] += 1
            continue
        repository = _field(row, "repository_name", "repo", "repository")
        path = _field(row, "func_path_in_repository", "path", "file_path")
        function_id = _field(row, "func_name", "function_name", "func_code_url", "url")
        if not repository or not path or not function_id:
            reasons["missing_provenance"] += 1
            continue
        code_sha = hashlib.sha256(code.encode()).hexdigest()
        records.append(
            FunctionRecord(
                split=_field(row, "_split", "split_name", "partition"),
                repository=repository,
                path=path,
                function_id=function_id,
                code=code,
                code_sha256=code_sha,
                normalized_ast_sha256=ast_sha,
                token_count=token_count,
                cyclomatic_complexity=float(primitive[0]),
                max_control_depth=float(primitive[1]),
                distinct_call_sites=float(primitive[2]),
            )
        )
    return records, reasons


def remove_cross_split_duplicates(
    records_by_split: dict[str, list[FunctionRecord]],
) -> tuple[dict[str, list[FunctionRecord]], dict[str, Any]]:
    owners: dict[str, set[str]] = {}
    for split, records in records_by_split.items():
        for record in records:
            owners.setdefault(record.normalized_ast_sha256, set()).add(split)
    cross_split = {digest for digest, splits in owners.items() if len(splits) > 1}
    filtered = {
        split: [r for r in records if r.normalized_ast_sha256 not in cross_split]
        for split, records in records_by_split.items()
    }
    return filtered, {
        "cross_split_ast_count": len(cross_split),
        "removed_by_split": {
            split: len(records_by_split[split]) - len(filtered[split]) for split in filtered
        },
    }


def deterministic_limit(records: list[FunctionRecord], limit: int) -> list[FunctionRecord]:
    return sorted(records, key=lambda record: record.stable_key)[:limit]


def robust_scale_fit(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    median = np.median(values, axis=0)
    q25, q75 = np.percentile(values, (25, 75), axis=0)
    scale = np.maximum(q75 - q25, 1.0)
    return median, scale


def robust_scale(values: np.ndarray, median: np.ndarray, scale: np.ndarray) -> np.ndarray:
    return (values - median) / scale


def embed_code(
    records: list[FunctionRecord],
    *,
    model_id: str,
    revision: str,
    batch_size: int,
    device: str,
) -> tuple[np.ndarray, dict[str, str]]:
    try:
        import torch
        from transformers import AutoModel, AutoTokenizer
    except ImportError as exc:  # pragma: no cover - exercised only in full environment
        raise RuntimeError(
            "install the option-b dependencies with pip install -e '.[option-b]'"
        ) from exc

    tokenizer = AutoTokenizer.from_pretrained(model_id, revision=revision)
    model = AutoModel.from_pretrained(model_id, revision=revision).to(device)
    model.eval()
    outputs: list[np.ndarray] = []
    with torch.inference_mode():
        for start in range(0, len(records), batch_size):
            batch = records[start : start + batch_size]
            encoded = tokenizer(
                [record.code for record in batch],
                padding=True,
                truncation=True,
                max_length=256,
                return_tensors="pt",
            )
            encoded = {name: tensor.to(device) for name, tensor in encoded.items()}
            hidden = model(**encoded).last_hidden_state
            mask = encoded["attention_mask"].unsqueeze(-1)
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
            outputs.append(pooled.cpu().numpy().astype(np.float32))
    embeddings = np.concatenate(outputs, axis=0)
    return embeddings, {
        "model_id": model_id,
        "revision": revision,
        "torch": torch.__version__,
        "transformers": __import__("transformers").__version__,
    }


def fit_primitive_probes(
    train_x: np.ndarray,
    train_y: np.ndarray,
    validation_x: np.ndarray,
    validation_y: np.ndarray,
    test_x: np.ndarray,
    alphas: tuple[float, ...],
) -> tuple[np.ndarray, dict[str, Any]]:
    predictions = np.empty((len(test_x), train_y.shape[1]), dtype=np.float64)
    report: dict[str, Any] = {}
    for index, name in enumerate(PRIMITIVES):
        candidates: list[tuple[float, float, Ridge]] = []
        for alpha in alphas:
            model = Ridge(alpha=alpha).fit(train_x, train_y[:, index])
            validation_prediction = model.predict(validation_x)
            mae = mean_absolute_error(validation_y[:, index], validation_prediction)
            candidates.append((float(mae), -alpha, model))
        _, _, selected = min(candidates, key=lambda item: (item[0], item[1]))
        test_prediction = selected.predict(test_x)
        predictions[:, index] = test_prediction
        validation_prediction = selected.predict(validation_x)
        report[name] = {
            "selected_alpha": float(selected.alpha),
            "validation_mae": float(
                mean_absolute_error(validation_y[:, index], validation_prediction)
            ),
            "validation_r2": float(r2_score(validation_y[:, index], validation_prediction)),
            "validation_spearman": float(
                spearmanr(validation_y[:, index], validation_prediction).statistic
            ),
            "test_prediction_sha256": array_hash(test_prediction),
            "coefficient_sha256": array_hash(np.asarray(selected.coef_, dtype=np.float64)),
        }
    return predictions, report


def chebyshev_distance(queries: np.ndarray, candidates: np.ndarray) -> np.ndarray:
    return np.max(np.abs(queries[:, None, :] - candidates[None, :, :]), axis=2)


def cosine_distance(queries: np.ndarray, candidates: np.ndarray) -> np.ndarray:
    q = queries / np.maximum(np.linalg.norm(queries, axis=1, keepdims=True), np.finfo(float).eps)
    c = candidates / np.maximum(
        np.linalg.norm(candidates, axis=1, keepdims=True), np.finfo(float).eps
    )
    return 1.0 - q @ c.T


def euclidean_distance(queries: np.ndarray, candidates: np.ndarray) -> np.ndarray:
    squared = np.maximum(
        np.sum(queries * queries, axis=1, keepdims=True)
        + np.sum(candidates * candidates, axis=1)[None, :]
        - 2.0 * queries @ candidates.T,
        0.0,
    )
    return np.sqrt(squared)


def build_hard_negative_manifest(
    oracle: np.ndarray,
    query_token_counts: np.ndarray,
    candidate_token_counts: np.ndarray,
    config: OptionBConfig,
) -> list[dict[str, int]]:
    boundaries = np.quantile(candidate_token_counts, np.linspace(0.0, 1.0, 11))
    manifest: list[dict[str, int]] = []
    for query_index, query_length in enumerate(query_token_counts):
        decile = min(int(np.searchsorted(boundaries[1:-1], query_length, side="right")), 9)
        candidate_deciles = np.minimum(
            np.searchsorted(boundaries[1:-1], candidate_token_counts, side="right"), 9
        )
        pool = np.flatnonzero(candidate_deciles == decile)
        if len(pool) < 2:
            continue
        ranked = pool[np.argsort(oracle[query_index, pool], kind="stable")]
        pairs: list[tuple[str, int, int]] = []
        for left_rank in range(len(ranked)):
            for separation in range(config.min_rank_separation, config.max_rank_separation + 1):
                right_rank = left_rank + separation
                if right_rank >= len(ranked):
                    break
                left = int(ranked[left_rank])
                right = int(ranked[right_rank])
                if oracle[query_index, left] == oracle[query_index, right]:
                    continue
                key = hashlib.sha256(
                    f"{MANIFEST_SEED}:{query_index}:{left}:{right}".encode()
                ).hexdigest()
                pairs.append((key, left, right))
        for _, left, right in sorted(pairs)[: config.max_pairs_per_query]:
            manifest.append({"query": query_index, "closer": left, "farther": right})
    return manifest


def manifest_triplet_accuracy(distances: np.ndarray, manifest: list[dict[str, int]]) -> float:
    if not manifest:
        return float("nan")
    scores: list[float] = []
    for item in manifest:
        left = distances[item["query"], item["closer"]]
        right = distances[item["query"], item["farther"]]
        scores.append(0.5 if left == right else float(left < right))
    return float(np.mean(scores))


def array_hash(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    payload = (
        json.dumps(
            {"dtype": str(array.dtype), "shape": list(array.shape)},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        + array.tobytes()
    )
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, value: Any) -> str:
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return hashlib.sha256(payload.encode()).hexdigest()


def environment_manifest() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": np.__version__,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-contract", action="store_true")
    args = parser.parse_args()
    if args.print_contract:
        print(json.dumps(asdict(OptionBConfig()), indent=2, sort_keys=True))
        return
    parser.error(
        "canonical execution is intentionally split into prepare/embed/evaluate commands; "
        "use the scripts documented in docs/runbooks/option-b-real-code.md"
    )


if __name__ == "__main__":
    main()

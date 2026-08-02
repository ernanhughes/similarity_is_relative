from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest

from relate.experiments import option_c0_d1_integrity_audit as d1


def sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


@dataclass(frozen=True)
class FakeRecord:
    repository: str
    stable_key: str
    source_split: str
    path: str
    function_id: str
    code: str
    code_sha256: str
    normalized_ast_sha256: str
    token_count: int


@dataclass(frozen=True)
class FakeVisible:
    role: str
    record: FakeRecord


def row(
    role: str,
    repository: str,
    stable_key: str,
    code: str,
    *,
    ast: str | None = None,
) -> d1.VisibleAuditRow:
    return d1.VisibleAuditRow(
        role=role,
        repository=repository,
        stable_key=stable_key,
        source_split="train",
        path=f"{stable_key}.py",
        function_id=stable_key,
        code_sha256=sha(code),
        normalized_ast_sha256=sha(ast or code),
        token_count=len(code.split()),
        simhash_hex=d1.token_simhash(code),
    )


def fake_visible(role: str, repository: str, stable_key: str, code: str) -> FakeVisible:
    return FakeVisible(
        role=role,
        record=FakeRecord(
            repository=repository,
            stable_key=stable_key,
            source_split="train",
            path=f"{stable_key}.py",
            function_id=stable_key,
            code=code,
            code_sha256=sha(code),
            normalized_ast_sha256=sha(code),
            token_count=len(code.split()),
        ),
    )


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in rows),
        encoding="utf-8",
    )


def context(
    tmp_path: Path,
    *,
    source: str = "source",
    allocation: str = "allocation",
) -> d1.AuditContext:
    identity = tmp_path / "identity.json"
    manifest = tmp_path / "allocation.jsonl"
    identity.write_text(source, encoding="utf-8")
    manifest.write_text(allocation, encoding="utf-8")
    return d1._audit_context(
        identity,
        manifest,
        near_hamming=3,
        near_max_bucket=20,
        near_max_pairs=50,
    )


def test_visible_row_rejects_hidden_roles() -> None:
    with pytest.raises(ValueError, match="hidden"):
        row("c0_selection", "owner/repo", "a", "def f():\n    return 1\n")


def test_family_diagnostics_use_names_only_and_label_heuristic() -> None:
    report = d1.repository_family_report(
        [
            {"role": "c0_fit", "repository": "alice/tool"},
            {"role": "c0_iteration", "repository": "bob/tool-fork"},
            {"role": "c1_reserve", "repository": "carol/tool-v2"},
        ]
    )
    assert report["uses_published_repository_names_only"] is True
    assert report["hidden_row_content_accessed"] is False
    assert report["heuristic_candidates_are_not_proof_of_relatedness"] is True
    assert report["suffix_stripped_cross_role_groups"] == 1


def test_sqlite_wal_and_exact_context_resume(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    visible = [
        fake_visible("c0_fit", "a/repo", "fit-1", "def f(x):\n    return x + 1\n"),
        fake_visible("c0_iteration", "b/repo", "iter-1", "def g(x):\n    return x + 2\n"),
    ]
    assignments = [
        {"role": "c0_fit", "repository": "a/repo", "row_count": 1},
        {"role": "c0_iteration", "repository": "b/repo", "row_count": 1},
    ]
    calls = 0

    def reconstruct(
        _identity: Path,
        _firewall: Path,
    ) -> tuple[list[FakeVisible], dict[str, object]]:
        nonlocal calls
        calls += 1
        return visible, {"visible_rows": {"c0_fit": 1, "c0_iteration": 1}}

    monkeypatch.setattr(d1.discovery_runner, "reconstruct_visible_records", reconstruct)
    ctx = context(tmp_path)
    with d1.IntegrityAuditCache(tmp_path / "cache.sqlite3") as cache:
        assert cache.connection.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        cache.register_context(ctx)
        rows1, meta1 = d1.load_or_reconstruct_visible_rows(
            tmp_path / "identity.json",
            tmp_path,
            assignments,
            cache=cache,
            context=ctx,
            reporter=d1.ProgressReporter(),
        )
        rows2, meta2 = d1.load_or_reconstruct_visible_rows(
            tmp_path / "identity.json",
            tmp_path,
            assignments,
            cache=cache,
            context=ctx,
            reporter=d1.ProgressReporter(),
        )
    assert calls == 1
    assert meta1["cache_misses"] == 2
    assert meta2["cache_hits"] == 2
    assert rows1 == rows2


def test_changed_context_inputs_change_context(tmp_path: Path) -> None:
    base = context(tmp_path, source="a", allocation="b")
    changed_source = context(tmp_path, source="changed", allocation="b")
    changed_allocation = context(tmp_path, source="changed", allocation="changed")
    near_changed = d1._audit_context(
        tmp_path / "identity.json",
        tmp_path / "allocation.jsonl",
        near_hamming=4,
        near_max_bucket=20,
        near_max_pairs=50,
    )
    observed = {
        base.sha256,
        changed_source.sha256,
        changed_allocation.sha256,
        near_changed.sha256,
    }
    assert len(observed) == 4


def test_incomplete_cached_rows_are_not_complete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assignments = [
        {"role": "c0_fit", "repository": "a/repo", "row_count": 1},
        {"role": "c0_iteration", "repository": "b/repo", "row_count": 1},
    ]
    calls = 0

    def reconstruct(
        _identity: Path,
        _firewall: Path,
    ) -> tuple[list[FakeVisible], dict[str, object]]:
        nonlocal calls
        calls += 1
        return [
            fake_visible("c0_fit", "a/repo", "fit-1", "def f():\n    return 1\n"),
            fake_visible("c0_iteration", "b/repo", "iter-1", "def g():\n    return 2\n"),
        ], {}

    monkeypatch.setattr(d1.discovery_runner, "reconstruct_visible_records", reconstruct)
    ctx = context(tmp_path)
    with d1.IntegrityAuditCache(tmp_path / "cache.sqlite3") as cache:
        cache.register_context(ctx)
        cache.put_visible_rows(
            ctx.sha256,
            [row("c0_fit", "a/repo", "fit-1", "def f():\n    return 1\n")],
        )
        rows, meta = d1.load_or_reconstruct_visible_rows(
            tmp_path / "identity.json",
            tmp_path,
            assignments,
            cache=cache,
            context=ctx,
            reporter=d1.ProgressReporter(),
        )
    assert calls == 1
    assert len(rows) == 2
    assert meta["reconstructed"] is True


def test_corrupt_context_state_is_rejected(tmp_path: Path) -> None:
    ctx = context(tmp_path)
    with d1.IntegrityAuditCache(tmp_path / "cache.sqlite3") as cache:
        cache.register_context(ctx)
        cache.connection.execute(
            "UPDATE contexts SET payload_json = ? WHERE context_sha256 = ?",
            ("{}", ctx.sha256),
        )
        cache.connection.commit()
        with pytest.raises(ValueError, match="collision|corruption"):
            cache.register_context(ctx)


def test_completed_near_scan_resumes_without_recompute(tmp_path: Path) -> None:
    rows = [
        row("c0_fit", "a/repo", "fit-1", "def f(x):\n    return x + 1\n"),
        row("c0_iteration", "b/repo", "iter-1", "def f(x):\n    return x + 1\n"),
    ]
    ctx = context(tmp_path)
    with d1.IntegrityAuditCache(tmp_path / "cache.sqlite3") as cache:
        cache.register_context(ctx)
        first = d1.near_duplicate_report(
            rows,
            cache=cache,
            context=ctx,
            max_hamming=64,
            max_bucket=20,
            max_pairs=50,
            reporter=d1.ProgressReporter(),
        )
        second = d1.near_duplicate_report(
            rows,
            cache=cache,
            context=ctx,
            max_hamming=64,
            max_bucket=20,
            max_pairs=50,
            reporter=d1.ProgressReporter(),
        )
    assert first["cache_reused"] is False
    assert second["cache_reused"] is True
    assert second["near_duplicate_scan_complete"] is True


def test_exact_duplicates_and_bounded_samples_are_deterministic() -> None:
    same_code = "def f():\n    return 1\n"
    rows = [
        row("c0_fit", "a/repo", "fit-1", same_code),
        row("c0_iteration", "b/repo", "iter-1", same_code),
        row("c0_fit", "a/repo", "fit-2", same_code),
        row("c0_fit", "a/repo", "fit-3", "def z():\n    return 3\n"),
    ]
    report = d1.exact_overlap_report(rows, field="code_sha256", sample_limit=1)
    assert report["cross_role_hashes"] == 1
    assert report["cross_role_rows"] == 3
    assert len(report["samples"]) == 1
    assert report["samples"][0]["stable_keys"] == ["fit-1", "fit-2", "iter-1"]


def test_within_role_duplicates_are_not_cross_role() -> None:
    same_code = "def f():\n    return 1\n"
    rows = [
        row("c0_fit", "a/repo", "fit-1", same_code),
        row("c0_fit", "a/repo", "fit-2", same_code),
        row("c0_iteration", "b/repo", "iter-1", "def g():\n    return 2\n"),
    ]
    assert d1.exact_overlap_report(rows, field="code_sha256")["cross_role_hashes"] == 0


def test_near_duplicate_fingerprints_and_order_are_deterministic(tmp_path: Path) -> None:
    assert d1.token_simhash("def f(x):\n    return x + 1\n") == d1.token_simhash(
        "def f(y):\n    return y + 1\n"
    )
    rows = [
        row("c0_fit", "a/repo", "fit-1", "def f(x):\n    return x + 1\n"),
        row("c0_iteration", "b/repo", "iter-1", "def f(y):\n    return y + 1\n"),
        row("c0_iteration", "c/repo", "iter-2", "class A:\n    pass\n"),
    ]
    ctx = context(tmp_path)
    with d1.IntegrityAuditCache(tmp_path / "cache.sqlite3") as cache:
        cache.register_context(ctx)
        report = d1.near_duplicate_report(
            rows,
            cache=cache,
            context=ctx,
            max_hamming=3,
            max_bucket=20,
            max_pairs=50,
            reporter=d1.ProgressReporter(),
        )
    assert report["near_pairs"] == 1
    assert report["samples"][0]["left"]["stable_key"] == "fit-1"
    assert d1.simhash_hamming("0000000000000000", "000000000000000f") == 4


def test_oversized_bucket_and_pair_truncation_mark_scan_incomplete(tmp_path: Path) -> None:
    same = "def f(x):\n    return x + 1\n"
    rows = [
        row("c0_fit", "a/repo", "fit-1", same),
        row("c0_iteration", "b/repo", "iter-1", same),
        row("c0_iteration", "c/repo", "iter-2", same),
    ]
    ctx = context(tmp_path)
    with d1.IntegrityAuditCache(tmp_path / "cache.sqlite3") as cache:
        cache.register_context(ctx)
        oversized = d1.near_duplicate_report(
            rows,
            cache=cache,
            context=ctx,
            max_hamming=64,
            max_bucket=1,
            max_pairs=50,
            reporter=d1.ProgressReporter(),
        )
    assert oversized["near_duplicate_scan_complete"] is False
    assert oversized["oversized_buckets_skipped"] > 0

    ctx2 = d1._audit_context(
        tmp_path / "identity.json",
        tmp_path / "allocation.jsonl",
        near_hamming=64,
        near_max_bucket=20,
        near_max_pairs=1,
    )
    with d1.IntegrityAuditCache(tmp_path / "cache2.sqlite3") as cache:
        cache.register_context(ctx2)
        truncated = d1.near_duplicate_report(
            rows,
            cache=cache,
            context=ctx2,
            max_hamming=64,
            max_bucket=20,
            max_pairs=1,
            reporter=d1.ProgressReporter(),
        )
    assert truncated["near_duplicate_scan_complete"] is False
    assert truncated["pair_truncated"] is True


def test_repository_suffixes_are_stripped() -> None:
    assert d1.repository_signatures("owner/project-v2")[1] == "project"
    assert d1.repository_signatures("owner/project-mirror")[1] == "project"
    assert d1.repository_signatures("owner/project-backup")[1] == "project"


def test_hash_paths_at_ref_uses_git_object_bytes(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "a@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "A"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "core.autocrlf", "false"], cwd=tmp_path, check=True)
    target = tmp_path / "file.txt"
    target.write_bytes(b"exact\r\nbytes\n")
    subprocess.run(["git", "add", "file.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "add"], cwd=tmp_path, check=True, capture_output=True)
    ref = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    manifest = d1._hash_paths_at_ref(
        tmp_path,
        ref,
        ["file.txt", "missing.py"],
        d1.ProgressReporter(),
    )
    assert manifest["file.txt"]["sha256"] == hashlib.sha256(b"exact\r\nbytes\n").hexdigest()
    assert manifest["file.txt"]["git_ref"] == ref
    assert manifest["missing.py"]["available"] is False


def test_dirty_worktree_refused_unless_override(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "a@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "A"], cwd=tmp_path, check=True)
    (tmp_path / "tracked.txt").write_text("clean\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt"], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-m", "add"], cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "tracked.txt").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(ValueError, match="clean Git worktree"):
        d1.execution_source_manifest(
            tmp_path,
            v1_execution_ref="HEAD",
            allow_dirty=False,
            reporter=d1.ProgressReporter(),
        )
    manifest = d1.execution_source_manifest(
        tmp_path,
        v1_execution_ref="HEAD",
        allow_dirty=True,
        reporter=d1.ProgressReporter(),
    )
    assert manifest["worktree_clean"] is False


def test_progress_output_contains_phase_percentage_elapsed_eta_and_cache(
    capsys: pytest.CaptureFixture[str],
) -> None:
    reporter = d1.ProgressReporter()
    started = 0.0
    reporter.rows("cache visible rows", 5, 10, started=started, cache_hits=2, cache_misses=8)
    output = capsys.readouterr().err
    assert "cache visible rows" in output
    assert "50.0%" in output
    assert "elapsed=" in output
    assert "eta=" in output
    assert "cache=2 hit/8 miss" in output


def test_existing_output_is_never_overwritten(tmp_path: Path) -> None:
    output = tmp_path / "result.json"
    output.write_text("exists", encoding="utf-8")
    with pytest.raises(FileExistsError):
        d1.run_d1_integrity_audit(
            identity_path=tmp_path / "identity.json",
            firewall_dir=tmp_path,
            allocation_path=tmp_path / "allocation.jsonl",
            output_path=output,
            allow_dirty=True,
        )


def test_result_schema_firewall_booleans_and_no_contamination_conclusion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    identity = tmp_path / "identity.json"
    identity.write_text("identity", encoding="utf-8")
    firewall = tmp_path / "firewall"
    firewall.mkdir()
    allocation = firewall / "option-c0-repository-allocation-v1.jsonl"
    write_jsonl(
        allocation,
        [
            {"role": "c0_fit", "repository": "a/repo", "row_count": 1},
            {"role": "c0_iteration", "repository": "b/repo", "row_count": 1},
            {"role": "c0_selection", "repository": "hidden/repo", "row_count": 1},
        ],
    )

    def reconstruct(
        _identity: Path,
        _firewall: Path,
    ) -> tuple[list[FakeVisible], dict[str, object]]:
        return [
            fake_visible("c0_fit", "a/repo", "fit-1", "def f():\n    return 1\n"),
            fake_visible("c0_iteration", "b/repo", "iter-1", "def g():\n    return 2\n"),
        ], {}

    monkeypatch.setattr(d1.discovery_runner, "reconstruct_visible_records", reconstruct)
    monkeypatch.setattr(
        d1,
        "execution_source_manifest",
        lambda *_args, **_kwargs: {
            "v1_all_paths_available": False,
            "d1_all_paths_available": True,
            "worktree_clean": True,
        },
    )
    result = d1.run_d1_integrity_audit(
        identity_path=identity,
        firewall_dir=firewall,
        allocation_path=allocation,
        output_path=tmp_path / "result.json",
        cache_path=tmp_path / "cache.sqlite3",
        allow_dirty=True,
        near_hamming=3,
        near_max_bucket=20,
        near_max_pairs=50,
    )
    assert result["scientific_result_observed"] is False
    assert result["mechanism_result_observed"] is False
    assert result["c0_selection_rows_accessed"] is False
    assert result["c1_rows_accessed"] is False
    assert result["hidden_row_content_accessed"] is False
    assert result["automatic_material_contamination_decision"] == "NOT_PERMITTED"

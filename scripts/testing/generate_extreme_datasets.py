#!/usr/bin/env python3
"""Synthesize extreme / rare-case datasets for the Dynamic Data Analysis pipeline.

These exercise robustness gaps NOT covered by the existing happy-path and
rare-case sweeps: extreme shapes (wide/empty/single-row), null-heavy columns,
degenerate dtypes (zero variance, mixed types, infinities), encoding variants
(UTF-16, Latin-1, BOM), delimiter footguns (CRLF, quoted separators, European
decimal comma), and malformed headers (duplicate, blank, whitespace).

Deterministic: fixed seed, no network. Re-run is idempotent (overwrites).

Output: test_resources/datasets/extreme/*.csv (+ a manifest.json)

Usage: python scripts/testing/generate_extreme_datasets.py
"""
from __future__ import annotations

import csv
import json
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = PROJECT_ROOT / "test_resources" / "datasets" / "extreme"

SEED = 1729
rng = random.Random(SEED)


def _w(name: str, text: str, encoding: str = "utf-8", newline: str = "\n") -> dict:
    """Write a CSV from already-rendered text (full control over bytes)."""
    path = OUT_DIR / name
    data = text.replace("\n", newline)
    path.write_bytes(data.encode(encoding))
    return {"file": name, "encoding": encoding, "bytes": path.stat().st_size}


def _rows_csv(name: str, header: list[str], rows: list[list], **kw) -> dict:
    import io

    buf = io.StringIO()
    wr = csv.writer(buf, lineterminator="\n")
    wr.writerow(header)
    for r in rows:
        wr.writerow(r)
    return _w(name, buf.getvalue(), **kw)


def gen() -> list[dict]:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []

    # 1) Wide table: 120 numeric columns x 150 rows (heatmap/rendering/perf stress)
    cols = [f"f{i:03d}" for i in range(120)]
    rows = [[round(rng.gauss(i, 5 + (i % 7)), 3) for i in range(120)] for _ in range(150)]
    manifest.append(_rows_csv("wide_120col.csv", cols, rows) | {"why": "120 numeric cols — heatmap/render/perf stress"})

    # 2) Zero data rows (header only)
    manifest.append(_rows_csv("zero_rows.csv", ["a", "b", "c"], []) | {"why": "header only, 0 data rows"})

    # 3) Single data row
    manifest.append(_rows_csv("single_row.csv", ["x", "y", "label"], [[1.0, 2.0, "yes"]]) | {"why": "exactly 1 data row"})

    # 4) Two rows (below model floor=20, above empty)
    manifest.append(
        _rows_csv("two_rows.csv", ["x", "y", "target"], [[1, 2, "a"], [3, 4, "b"]]) | {"why": "2 rows; below model floor"}
    )

    # 5) Entirely-null numeric column alongside normal columns
    rows = [[rng.randint(1, 100), "", rng.choice(["red", "blue", "green"])] for _ in range(80)]
    manifest.append(_rows_csv("all_null_col.csv", ["count", "empty_metric", "color"], rows) | {"why": "one entirely-null numeric column"})

    # 6) 95%-null column
    rows = []
    for i in range(120):
        sparse = rng.gauss(50, 10) if i % 20 == 0 else ""
        rows.append([i, round(rng.gauss(10, 3), 2), sparse])
    manifest.append(_rows_csv("mostly_null.csv", ["id", "dense", "sparse_95pct_null"], rows) | {"why": "column ~95% null"})

    # 7) Zero-variance numeric column (constant) + a real signal column
    rows = [[42, round(rng.gauss(i / 10, 2), 3), rng.choice(["A", "B"])] for i in range(100)]
    manifest.append(_rows_csv("zero_variance.csv", ["constant", "signal", "grp"], rows) | {"why": "constant column (zero variance)"})

    # 8) High-cardinality categorical (~4000 unique over 4000 rows)
    rows = [[f"user_{i:05d}", round(rng.gauss(100, 30), 2), rng.choice(["paid", "free"])] for i in range(4000)]
    manifest.append(_rows_csv("high_cardinality.csv", ["user_token", "spend", "plan"], rows) | {"why": "categorical with ~4000 unique values"})

    # 9) Mixed-dtype column: ints, floats, strings, blanks interleaved
    rows = []
    pool = [1, 2.5, "n/a", "", 3, "missing", 4.0, "?", 5]
    for i in range(100):
        rows.append([i, pool[i % len(pool)], rng.choice(["x", "y"])])
    manifest.append(_rows_csv("mixed_dtype_col.csv", ["idx", "messy_value", "cat"], rows) | {"why": "column mixes int/float/str/blank"})

    # 10) Ambiguous date formats (DD/MM vs MM/DD)
    rows = []
    for i in range(60):
        d = f"{(i % 12) + 1:02d}/{(i % 28) + 1:02d}/2020"
        rows.append([d, round(rng.gauss(20, 5), 2)])
    manifest.append(_rows_csv("ambiguous_dates.csv", ["date", "value"], rows) | {"why": "ambiguous DD/MM vs MM/DD dates"})

    # 11) UTF-16 LE encoded (metadata only tries utf-8/utf-8-sig/latin-1)
    txt = "name,score\nAlice,90\nBob,75\nCarol,88\n"
    manifest.append(_w("utf16_le.csv", txt, encoding="utf-16-le") | {"why": "UTF-16 LE — outside the 3-encoding fallback chain"})

    # 12) Latin-1 with accented characters
    txt = "city,population\nMontréal,1780000\nQuébec,540000\nTrois-Rivières,135000\n"
    manifest.append(_w("latin1_accents.csv", txt, encoding="latin-1") | {"why": "Latin-1 accented chars"})

    # 13) Windows CRLF line endings
    rows = [[i, round(rng.gauss(5, 1), 2), rng.choice(["on", "off"])] for i in range(50)]
    manifest.append(_rows_csv("crlf_endings.csv", ["i", "v", "state"], rows, newline="\r\n") | {"why": "Windows CRLF line endings"})

    # 14) Commas inside quoted fields (separator footgun)
    txt = (
        'company,note,revenue\n'
        '"Acme, Inc.","sells widgets, gadgets",1000000\n'
        '"Beta, LLC","does, things, here",2500000\n'
        '"Gamma Co","plain note",750000\n'
    )
    manifest.append(_w("quoted_commas.csv", txt) | {"why": "commas inside quoted fields"})

    # 15) European: semicolon separator + decimal comma
    txt = "produkt;preis;menge\nApfel;1,50;100\nBirne;2,30;50\nKirsche;5,99;25\n"
    manifest.append(_w("euro_semicolon_decimal.csv", txt) | {"why": "semicolon sep + decimal comma (European)"})

    # 16) Duplicate header names
    txt = "id,value,value\n1,10,11\n2,20,21\n3,30,31\n"
    manifest.append(_w("duplicate_headers.csv", txt) | {"why": "two columns share a name"})

    # 17) Blank / unnamed header cells
    txt = "id,,score,\n1,x,90,extra1\n2,y,75,extra2\n3,z,88,extra3\n"
    manifest.append(_w("blank_headers.csv", txt) | {"why": "empty header cells"})

    # 18) Whitespace-padded headers
    txt = " id , name ,  score  \n1,a,90\n2,b,75\n3,c,88\n"
    manifest.append(_w("whitespace_headers.csv", txt) | {"why": "headers padded with spaces"})

    # 19) UTF-8 BOM
    manifest.append(_w("utf8_bom.csv", "a,b\n1,2\n3,4\n", encoding="utf-8-sig") | {"why": "UTF-8 BOM prefix"})

    # 20) Infinities and extreme magnitudes
    rows = [["inf", 1e308, 0.0], ["-inf", -1e308, 1.5], ["normal", 42.0, 2.5]]
    rows += [[f"row{i}", round(rng.gauss(0, 1), 4), round(rng.gauss(0, 1), 4)] for i in range(40)]
    manifest.append(_rows_csv("inf_and_extremes.csv", ["kind", "huge", "small"], rows) | {"why": "inf / 1e308 / extreme magnitudes"})

    # 21) Single-column data (separator over-sniff footgun)
    rows = [[round(rng.gauss(100, 15), 1)] for _ in range(60)]
    manifest.append(_rows_csv("single_value_col.csv", ["measurement"], rows) | {"why": "single column — sniffer footgun"})

    # 22) Boolean-as-strings mixed vocab
    rows = []
    vocab = ["True", "False", "yes", "no", "Y", "N", "1", "0"]
    for i in range(80):
        rows.append([i, vocab[i % len(vocab)], round(rng.gauss(10, 2), 2)])
    manifest.append(_rows_csv("boolean_strings.csv", ["i", "flag", "amt"], rows) | {"why": "boolean expressed as mixed strings"})

    # 23) Ragged rows: clean header, then rows with varying column counts
    #     (host metadata has a python-engine fallback; sandbox loader may not)
    txt = (
        "a,b,c\n"
        "1,2,3\n"
        "4,5\n"               # short row
        "6,7,8,9,10\n"        # long row
        "11,12,13\n"
        "14\n"                # very short
        "15,16,17\n"
    )
    manifest.append(_w("ragged_rows.csv", txt) | {"why": "ragged rows after clean header — host/sandbox parse mismatch"})

    # 24) Malicious / injection-style column header (must be neutralized in code-gen)
    txt = (
        "value,__import__('os').system('id')#,price\n"
        "1,a,10.5\n"
        "2,b,20.0\n"
        "3,c,15.0\n"
    )
    manifest.append(_w("malicious_header.csv", txt) | {"why": "injection payload as a column name"})

    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    m = gen()
    print(f"Generated {len(m)} extreme datasets -> {OUT_DIR}")
    for d in m:
        print(f"  {d['file']:30s} {d['bytes']:>8d}B  {d.get('encoding','utf-8'):10s} {d['why']}")

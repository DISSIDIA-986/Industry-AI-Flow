#!/usr/bin/env python3
"""Download representative construction-industry seed documents for RAG QA."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import requests


@dataclass
class DocSpec:
    doc_id: str
    title: str
    source: str
    category: str
    kind: Literal["pdf", "html_text"]
    filename: str


SEED_DOCS: list[DocSpec] = [
    DocSpec(
        doc_id="gsa_core_2025_memo",
        title="GSA PBS Core Building Standards Memorandum (2025)",
        source="https://www.gsa.gov/system/files/PBS_Core_Building_Standards_Memorandum%2024FEB.25.pdf",
        category="federal_standards",
        kind="pdf",
        filename="gsa_core_building_standards_memo_2025.pdf",
    ),
    DocSpec(
        doc_id="gsa_p100_2024",
        title="GSA P100 Facilities Standards 2024 Final",
        source="https://www.gsa.gov/system/files/P100%202024%20Final%2010012024.pdf",
        category="federal_standards",
        kind="pdf",
        filename="gsa_p100_2024_final.pdf",
    ),
    DocSpec(
        doc_id="gsa_core_training_2025",
        title="GSA Interim Core Building Standards Training (2025-04-30)",
        source="https://www.gsa.gov/system/files/2025-04-30%20Revised%20PBS%20Interim%20Core%20Building%20Standards%20Training%20%281%29.pdf",
        category="federal_standards",
        kind="pdf",
        filename="gsa_core_building_training_2025-04-30.pdf",
    ),
    DocSpec(
        doc_id="caltrans_specs_2025",
        title="Caltrans 2025 Standard Specifications",
        source="https://dot.ca.gov/-/media/dot-media/programs/design/documents/2025_stdspecs.pdf",
        category="state_standards",
        kind="pdf",
        filename="caltrans_2025_standard_specifications.pdf",
    ),
    DocSpec(
        doc_id="caltrans_plans_2025",
        title="Caltrans 2025 Standard Plans (Locked)",
        source="https://dot.ca.gov/-/media/dot-media/programs/design/documents/2025-standard-plans-locked.pdf",
        category="state_standards",
        kind="pdf",
        filename="caltrans_2025_standard_plans_locked.pdf",
    ),
    DocSpec(
        doc_id="caltrans_specs_digest_2025",
        title="Caltrans 2025 Standard Specifications Digest",
        source="https://dot.ca.gov/-/media/dot-media/programs/design/documents/2025-standard-specifications-digest-a11y.pdf",
        category="state_standards",
        kind="pdf",
        filename="caltrans_2025_standard_specifications_digest.pdf",
    ),
    DocSpec(
        doc_id="caltrans_plans_digest_2025",
        title="Caltrans 2025 Standard Plans Digest",
        source="https://dot.ca.gov/-/media/dot-media/programs/design/documents/2025-standard-plans-digest-a11y.pdf",
        category="state_standards",
        kind="pdf",
        filename="caltrans_2025_standard_plans_digest.pdf",
    ),
    DocSpec(
        doc_id="ufgs_complete",
        title="DoD UFGS Complete",
        source="https://www.wbdg.org/FFC/DOD/UFGS/UFGS_COMPLETE.pdf",
        category="military_specs",
        kind="pdf",
        filename="ufgs_complete.pdf",
    ),
    DocSpec(
        doc_id="ufgs_toc",
        title="DoD UFGS Master Table of Contents",
        source="https://www.wbdg.org/FFC/DOD/UFGS/UFGS_TOC.pdf",
        category="military_specs",
        kind="pdf",
        filename="ufgs_toc.pdf",
    ),
    DocSpec(
        doc_id="ufgs_03_30_00",
        title="UFGS 03 30 00 Cast-In-Place Concrete",
        source="https://www.wbdg.org/FFC/DOD/UFGS/UFGS%2003%2030%2000.pdf",
        category="technical_specs",
        kind="pdf",
        filename="ufgs_03_30_00_cast_in_place_concrete.pdf",
    ),
    DocSpec(
        doc_id="osha_1926",
        title="OSHA Construction Standards 29 CFR 1926",
        source="https://www.osha.gov/laws-regs/regulations/standardnumber/1926/",
        category="safety_regulations",
        kind="html_text",
        filename="osha_29_cfr_1926.txt",
    ),
    DocSpec(
        doc_id="ifc_4_3_schema_specs",
        title="buildingSMART IFC 4.3 Schema Specifications",
        source="https://technical.buildingsmart.org/standards/ifc/ifc-schema-specifications/",
        category="bim_semantics",
        kind="html_text",
        filename="buildingsmart_ifc_4_3_schema_specifications.txt",
    ),
]


def _hash_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _html_to_text(content: str) -> str:
    # Strip non-content sections first, then tags. Minimal dependency approach.
    content = re.sub(r"(?is)<script.*?>.*?</script>", " ", content)
    content = re.sub(r"(?is)<style.*?>.*?</style>", " ", content)
    content = re.sub(r"(?i)<br\\s*/?>", "\n", content)
    content = re.sub(r"(?i)</p>", "\n\n", content)
    content = re.sub(r"(?is)<[^>]+>", " ", content)
    content = re.sub(r"&nbsp;", " ", content)
    content = re.sub(r"&amp;", "&", content)
    content = re.sub(r"&lt;", "<", content)
    content = re.sub(r"&gt;", ">", content)
    content = re.sub(r"\\s+\\n", "\n", content)
    content = re.sub(r"\\n{3,}", "\n\n", content)
    content = re.sub(r"[ \\t]{2,}", " ", content)
    return content.strip()


def download_doc(session: requests.Session, spec: DocSpec, output_dir: Path) -> dict:
    target_path = output_dir / spec.filename
    downloaded_at = datetime.now(timezone.utc).isoformat()
    record = asdict(spec)
    record["downloaded_at_utc"] = downloaded_at

    response = session.get(spec.source, timeout=(20, 180))
    response.raise_for_status()

    if spec.kind == "pdf":
        content = response.content
        target_path.write_bytes(content)
        record["size_bytes"] = len(content)
        record["sha256"] = _hash_bytes(content)
        record["saved_path"] = str(target_path)
        record["status"] = "success"
        return record

    text = _html_to_text(response.text)
    target_path.write_text(text, encoding="utf-8")
    encoded = text.encode("utf-8")
    record["size_bytes"] = len(encoded)
    record["sha256"] = _hash_bytes(encoded)
    record["saved_path"] = str(target_path)
    record["status"] = "success"
    return record


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download construction seed docs for RAG initialization."
    )
    parser.add_argument(
        "--output-dir",
        default="test_resources/documents/construction_seed_2026q1",
        help="Output directory for downloaded documents.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_dir": str(output_dir.resolve()),
        "documents": [],
    }

    failures = 0
    with requests.Session() as session:
        session.headers.update(
            {
                "User-Agent": (
                    "Industry-AI-Flow-RAG-SeedDownloader/1.0 "
                    "(QA initialization)"
                )
            }
        )
        for i, spec in enumerate(SEED_DOCS, 1):
            print(f"[{i:02d}/{len(SEED_DOCS)}] Downloading: {spec.title}")
            try:
                row = download_doc(session, spec, output_dir)
            except Exception as exc:  # pragma: no cover - network/runtime dependent
                failures += 1
                row = asdict(spec)
                row["status"] = "failed"
                row["error"] = str(exc)
                row["saved_path"] = str(output_dir / spec.filename)
            manifest["documents"].append(row)

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    ok = sum(1 for d in manifest["documents"] if d.get("status") == "success")
    print(f"Downloaded: {ok}/{len(SEED_DOCS)}")
    print(f"Manifest: {manifest_path}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

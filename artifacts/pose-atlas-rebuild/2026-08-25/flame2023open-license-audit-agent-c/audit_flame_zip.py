"""Read-only FLAME2023Open zip license audit; never unpickle model data."""

from __future__ import annotations

import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

import pdfplumber


HERE = Path(__file__).resolve().parent
ZIP_PATH = Path(r"C:\Users\hitos\OneDrive\桌面\墨寒桌面語音互動虛擬女友2026.07.28開始開發\FLAME2023Open.zip")
README_NAME = "FLAME2023_Open Readme.pdf"
ALLOWED = ["MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "CC0", "CC BY"]


def sha_stream(handle: object) -> str:
    digest = hashlib.sha256()
    while True:
        chunk = handle.read(1024 * 1024)  # type: ignore[attr-defined]
        if not chunk:
            return digest.hexdigest().upper()
        digest.update(chunk)


def main() -> int:
    zip_sha = hashlib.sha256(ZIP_PATH.read_bytes()).hexdigest().upper()
    with zipfile.ZipFile(ZIP_PATH) as archive:
        corrupt = archive.testzip()
        entries = []
        for info in archive.infolist():
            with archive.open(info) as stream:
                entry_sha = sha_stream(stream)
            entries.append({"name": info.filename, "size": info.file_size, "crc32": f"{info.CRC:08X}", "sha256": entry_sha})
        readme_bytes = archive.read(README_NAME)

    with pdfplumber.open(io.BytesIO(readme_bytes)) as pdf:
        page_texts = [page.extract_text() or "" for page in pdf.pages]
    readme_text = "\n".join(page_texts)
    claims_cc_by = "Creative Commons Attribution 4.0 International License" in readme_text
    links_model_terms = "https://flame.is.tue.mpg.de/modellicense.html" in readme_text

    manifest = {
        "schema": "mohan.third_party.archive_manifest/v1",
        "source_zip": str(ZIP_PATH),
        "zip_sha256": zip_sha,
        "zip_size": ZIP_PATH.stat().st_size,
        "zip_test": "PASS" if corrupt is None else f"FAIL:{corrupt}",
        "entry_count": len(entries),
        "entries": entries,
        "safety": "flame2023_Open.pkl was hashed as bytes only and never unpickled or imported",
    }
    (HERE / "zip-entry-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    admission = {
        "schema": "mohan.third_party.production_admission/v1",
        "component": "FLAME2023_Open local archive",
        "source_zip": str(ZIP_PATH),
        "zip_sha256": zip_sha,
        "allowed_license_policy": ALLOWED,
        "readme": {
            "archive_entry": README_NAME,
            "sha256": hashlib.sha256(readme_bytes).hexdigest().upper(),
            "pages": len(page_texts),
            "license_claim": "CC BY 4.0",
            "short_verbatim_excerpt_under_25_words": "FLAME2023_Open is available under a Creative Commons Attribution 4.0 International License.",
            "model_terms_url": "https://flame.is.tue.mpg.de/modellicense.html",
            "claims_cc_by_4": claims_cc_by,
            "links_additional_terms": links_model_terms,
        },
        "separate_layers": {
            "model_pickle": {
                "entry": "flame2023_Open.pkl",
                "license_evidence": "README claims CC BY 4.0 for FLAME2023_Open",
                "commercial_compatibility_if_standard_cc_by_4_only": "ALLOWED_WITH_ATTRIBUTION",
                "production_admission": "BLOCK_MISSING_FULL_LINKED_MODEL_TERMS_IN_ARCHIVE",
            },
            "topology": {
                "separate_entry_found": False,
                "production_admission": "BLOCK_NOT_SEPARATELY_IDENTIFIABLE_OR_LICENSE_VERIFIABLE",
            },
            "landmark_embedding": {
                "separate_entry_found": False,
                "production_admission": "BLOCK_NOT_PRESENT",
            },
        },
        "missing_evidence": [
            "Full text of the linked modellicense.html terms is not included in the archive",
            "No standalone LICENSE/LICENCE/COPYING file is included",
            "No separately identifiable topology file is included",
            "No static or dynamic landmark embedding file is included",
        ],
        "overall_status": "BLOCK_DO_NOT_USE_ANY_ARCHIVE_DATA",
        "reason": "The README's CC BY 4.0 claim is on the user's allowlist, but the archive requires agreement to linked terms whose full text is absent locally; topology and embeddings cannot be separately verified.",
        "infectious_or_nc_detected": False,
        "formal_assets_modified": False,
        "archive_data_used": False,
        "audit_exit": 4,
    }
    (HERE / "flame2023open-production-admission.json").write_text(json.dumps(admission, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    report = """# FLAME2023Open local license audit

## 結論

**BLOCK - 不得使用壓縮檔內任何模型、拓撲或 embedding 資料。**

壓縮檔 README 明示 CC BY 4.0；若只有標準 CC BY 4.0，符合使用者准入清單並可商用但必須署名。然而 README 同時要求使用者閱讀並同意外部 `modellicense.html` 條款，而完整條款沒有收在壓縮檔中。依 fail-closed 原則，不能只憑授權名稱跳過缺失條款。

## 實際內容

- 真正資料檔只有 `flame2023_Open.pkl`。
- 沒有獨立 LICENSE/LICENCE/COPYING。
- 沒有獨立 topology 檔。
- 沒有 static/dynamic landmark embedding。
- pickle 只按位元組計算雜湊，沒有反序列化或執行。

## 判定邊界

- 未發現 NC、GPL、AGPL、LGPL 或 SA 聲明。
- 但「未發現禁用字樣」不等於准入；缺少完整連結條款仍然 BLOCK。
- 本次沒有把任何 FLAME 資料解壓到正式專案，也沒有修改正式 assets。
"""
    (HERE / "REPORT.md").write_text(report, encoding="utf-8")
    print(json.dumps({"zip_test": manifest["zip_test"], "entry_count": len(entries), "overall_status": admission["overall_status"], "audit_exit": 4}, ensure_ascii=False))
    return 4


if __name__ == "__main__":
    raise SystemExit(main())

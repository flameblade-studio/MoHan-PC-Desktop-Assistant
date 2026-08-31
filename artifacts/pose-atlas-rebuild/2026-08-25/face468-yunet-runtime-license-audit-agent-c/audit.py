from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(r"D:\FlamebladeStudio\CodexProjects\2026-08-13\mohan-multisensory-vision")
OUT = Path(__file__).resolve().parent
ALLOWED = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "CC0", "CC BY"}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest().upper()


def evidence(path: Path) -> dict[str, object]:
    return {
        "path": str(path),
        "exists": path.is_file(),
        "sha256": digest(path) if path.is_file() else None,
        "bytes": path.stat().st_size if path.is_file() else None,
    }


face = REPO / "assets/vision-models/face_landmark_468.tflite"
yunet = REPO / "assets/vision-models/face_detection_yunet_2023mar.onnx"
cv_dist = REPO / ".venv315/Lib/site-packages/opencv_python-5.0.0.93.dist-info"
cv_ffmpeg = REPO / ".venv315/Lib/site-packages/cv2/opencv_videoio_ffmpeg500_64.dll"
ort_dist = REPO / "tools/third_party/InstantMesh/.conda/Lib/site-packages/onnxruntime-1.23.2.dist-info"

probe = subprocess.run(
    [
        str(REPO / ".venv315/Scripts/python.exe"),
        "-c",
        (
            "import importlib.util,json;"
            "n=['cv2','onnxruntime','tensorflow','tflite_runtime','mediapipe'];"
            "print(json.dumps({x:(importlib.util.find_spec(x).origin if importlib.util.find_spec(x) else None) for x in n}))"
        ),
    ],
    capture_output=True,
    text=True,
    check=False,
)

payload = {
    "schema": "mohan.face-468-yunet-runtime-admission/v1",
    "policy": {
        "allowed": sorted(ALLOWED),
        "rejected": ["GPL", "AGPL", "LGPL", "CC BY-SA", "CC BY-ND", "CC BY-NC", "unknown"],
        "opencv_ffmpeg_rule": "Current OpenCV wheel contains LGPL FFmpeg and is forbidden for formal asset production.",
    },
    "models": [
        {
            "id": "mediapipe-face-landmark-468",
            **evidence(face),
            "expected_sha256": "1055CB9D4A9CA8B8C688902A3A5194311138BA256BCC94E336D8373A5F30C814",
            "source": "https://storage.googleapis.com/mediapipe-assets/face_landmark.tflite",
            "source_revision": "face_landmark.tflite",
            "license": "Apache-2.0",
            "model_admission": "PASS",
            "runtime_admission": "BLOCK",
            "reason": "No locally installed admitted TFLite runtime. OpenCV DNN is present but its wheel bundles forbidden LGPLv2.1 FFmpeg.",
        },
        {
            "id": "opencv-zoo-yunet-2023mar",
            **evidence(yunet),
            "expected_sha256": "8F2383E4DD3CFBB4553EA8718107FC0423210DC964F9F4280604804ED2552FA4",
            "source": "https://media.githubusercontent.com/media/opencv/opencv_zoo/f12e12798e8314f7c074a6656816c048dcc95b7a/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
            "source_revision": "f12e12798e8314f7c074a6656816c048dcc95b7a",
            "license": "MIT",
            "model_admission": "PASS",
            "runtime_admission": "BLOCK",
            "reason": "Project runtime is forbidden OpenCV wheel. A separate ONNX Runtime is locally present only in an isolated tool environment; its complete transitive production admission was not established here and it cannot execute the TFLite 468 model.",
        },
    ],
    "runtimes": [
        {
            "id": "opencv-python",
            "version": "5.0.0.93",
            "core_license": "Apache-2.0",
            "status": "DENY_FORMAL_ASSET_PRODUCTION",
            "blocking_component": "FFmpeg bundled in wheel under LGPLv2.1",
            "evidence": [
                evidence(cv_dist / "METADATA"),
                evidence(cv_dist / "LICENSE.txt"),
                evidence(cv_dist / "LICENSE-3RD-PARTY.txt"),
                evidence(cv_ffmpeg),
            ],
        },
        {
            "id": "onnxruntime",
            "version": "1.23.2",
            "declared_license": "MIT",
            "location": str(REPO / "tools/third_party/InstantMesh/.conda"),
            "status": "HOLD_NOT_PRODUCTION_ADMITTED",
            "limitations": [
                "Cannot execute TFLite face_landmark_468.tflite.",
                "Installed only in isolated third-party tool environment, not the formal MoHan runtime.",
                "Local wheel metadata has no bundled LICENSE/NOTICE file and transitive binary/dependency admission is incomplete.",
            ],
            "evidence": [evidence(ort_dist / "METADATA")],
        },
        {"id": "tensorflow", "status": "NOT_INSTALLED"},
        {"id": "tflite-runtime", "status": "NOT_INSTALLED"},
        {"id": "mediapipe", "status": "NOT_INSTALLED"},
    ],
    "probe": {
        "command": "<repo>/.venv315/Scripts/python.exe -c importlib.util.find_spec(...) ",
        "exit_code": probe.returncode,
        "stdout": probe.stdout.strip(),
        "stderr": probe.stderr.strip(),
    },
    "formal_468_identity_contour_gate": {
        "status": "BLOCK",
        "reason": "The admitted 468 model has no locally available runtime satisfying the allowlist; the only capable local route is forbidden OpenCV.",
    },
    "yunet_detector_gate": {
        "status": "BLOCK",
        "reason": "The model is admissible, but no fully admitted formal-runtime execution route is currently proven.",
    },
    "overall_status": "BLOCK",
    "exit_code": 4,
}

for model in payload["models"]:
    if model["sha256"] != model["expected_sha256"]:
        model["model_admission"] = "BLOCK_HASH_MISMATCH"

(OUT / "face468-yunet-runtime-admission.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps({"overall_status": payload["overall_status"], "output": str(OUT / "face468-yunet-runtime-admission.json")}, ensure_ascii=False))
raise SystemExit(4)

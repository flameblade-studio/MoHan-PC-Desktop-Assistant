"""續跑既有候選圖仍須通過其原產線閘門，所有模型與候選皆隔離。"""

from __future__ import annotations

lazy import sys
lazy from importlib import util
lazy from pathlib import Path
lazy from types import ModuleType, SimpleNamespace
lazy from unittest.mock import Mock

lazy import pytest


PRODUCTION_MODULES = (
    "chroma_mass_produce_v9",
    "produce_v10_geo",
    "produce_v11_geo",
    "produce_v12_c4",
)
SOURCE_ROOT = Path(__file__).resolve().parents[1] / "tools" / "second_gen_body"


def _module(monkeypatch, name: str) -> ModuleType:
    spec = util.spec_from_file_location(name, SOURCE_ROOT / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(params=PRODUCTION_MODULES)
def resumed_production(request, monkeypatch, tmp_path):
    monkeypatch.setenv("MOHAN_VISION_ROOT", str(tmp_path))
    lora = tmp_path / "identity.safetensors"
    lora.write_text("isolated fixture", encoding="utf-8")
    monkeypatch.setenv("MOHAN_IDENTITY_LORA", str(lora))
    monkeypatch.setattr(sys, "path", sys.path.copy())
    monkeypatch.syspath_prepend(str(SOURCE_ROOT))
    for name in ("thresholds", "tinted_init"):
        _module(monkeypatch, name)

    pipeline = Mock()
    diffusers = ModuleType("diffusers")
    diffusers.ChromaPipeline = Mock()
    diffusers.ChromaImg2ImgPipeline = Mock()
    diffusers.ChromaPipeline.from_pretrained.return_value = pipeline
    diffusers.ChromaImg2ImgPipeline.from_pretrained.return_value = pipeline
    diffusers.ChromaTransformer2DModel = Mock()
    diffusers.GGUFQuantizationConfig = Mock()
    monkeypatch.setitem(sys.modules, "diffusers", diffusers)
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(bfloat16="fixture"))
    monkeypatch.setitem(
        sys.modules, "lora_loader", SimpleNamespace(load_aitoolkit_chroma_lora=Mock())
    )

    loaded = {name: _module(monkeypatch, name) for name in PRODUCTION_MODULES}
    module = loaded[request.param]
    monkeypatch.setattr(
        module, "sys", SimpleNamespace(stdout=SimpleNamespace(reconfigure=Mock()))
    )
    if request.param == "chroma_mass_produce_v9":
        module.VIEWS = {0: "front"}
    elif request.param == "produce_v12_c4":
        module.VIEWS = [0]
        module.CONTROLS.mkdir(parents=True)
        (module.CONTROLS / "yaw+000-pitch+00_shaded-render.png").write_text(
            "isolated control fixture", encoding="utf-8"
        )
    else:
        (module.BUNDLES / "yaw+000-pitch+00").mkdir(parents=True)
    if hasattr(module, "control_mask"):
        module.control_mask = Mock(return_value="isolated mask")
    target = module.OUT / "body2-yaw+000.png"
    target.write_text("preserve candidate evidence", encoding="utf-8")
    entrypoint = module._run if request.param == "produce_v12_c4" else module.main
    return module, pipeline, target, entrypoint


def _gate(module, monkeypatch, *, accepted: bool) -> Mock:
    if module.__name__ in PRODUCTION_MODULES[:2]:
        verdict = "ok face-area=0.1" if accepted else "FAIL fixture view"
        gate = Mock(return_value=verdict)
        monkeypatch.setattr(module, "verify_view", gate)
    else:
        gate = Mock(return_value=("fixture 通過" if accepted else "fixture 不合格", accepted))
        monkeypatch.setattr(module, "check", gate)
    return gate


def test_existing_candidate_is_checked_before_acceptance(resumed_production, monkeypatch):
    module, pipeline, target, entrypoint = resumed_production
    gate = _gate(module, monkeypatch, accepted=True)

    entrypoint()

    gate.assert_called_once()
    assert gate.call_args.args[:2] == (target, 0)
    pipeline.assert_not_called()
    assert target.read_text(encoding="utf-8") == "preserve candidate evidence"


@pytest.mark.parametrize("verdict", ["FAIL fixture view", "unreadable"])
def test_existing_rejected_candidate_fails_closed(
    resumed_production, monkeypatch, capsys, verdict,
):
    module, pipeline, target, entrypoint = resumed_production
    gate = _gate(module, monkeypatch, accepted=False)
    if module.__name__ in PRODUCTION_MODULES[:2]:
        gate.return_value = verdict

    with pytest.raises(SystemExit) as error:
        entrypoint()

    assert error.value.code not in {None, 0}
    gate.assert_called_once()
    pipeline.assert_not_called()
    assert target.read_text(encoding="utf-8") == "preserve candidate evidence"
    output = capsys.readouterr().out
    assert "ALL VIEWS PASSED" not in output
    assert "全部通過" not in output


def test_existing_candidate_validation_errors_propagate(
    resumed_production, monkeypatch,
):
    module, pipeline, target, entrypoint = resumed_production
    gate = _gate(module, monkeypatch, accepted=True)
    gate.side_effect = ValueError("fixture unreadable")

    with pytest.raises(ValueError, match="fixture unreadable"):
        entrypoint()

    pipeline.assert_not_called()
    assert target.read_text(encoding="utf-8") == "preserve candidate evidence"

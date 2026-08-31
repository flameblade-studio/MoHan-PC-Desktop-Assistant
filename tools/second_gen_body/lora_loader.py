"""把 ai-toolkit 原生 Chroma LoRA 轉成 diffusers 命名並載入。

病史：ai-toolkit 輸出 `diffusion_model.double_blocks.N...` 原生命名，
diffusers 期待 `transformer.transformer_blocks.N.attn.to_q...`。
pipe.load_lora_weights() 對不上鍵時只印警告、靜默載入零個鍵——
2026-08-30 發現 v2～v5 全部量產其實都沒有 identity LoRA。
"""
from pathlib import Path

from safetensors.torch import load_file
from diffusers.loaders.lora_conversion_utils import (
    _convert_kohya_flux_lora_to_diffusers,
)

__all__ = ("load_aitoolkit_chroma_lora",)


def _to_kohya_naming(state_dict: dict) -> dict:
    converted = {}
    for key, value in state_dict.items():
        name = key.replace("diffusion_model.", "lora_unet_", 1)
        head, sep, _ = name.rpartition(".lora_A.weight")
        if sep:
            converted[head.replace(".", "_") + ".lora_down.weight"] = value
            continue
        head, sep, _ = name.rpartition(".lora_B.weight")
        if sep:
            converted[head.replace(".", "_") + ".lora_up.weight"] = value
    return converted


def load_aitoolkit_chroma_lora(
    pipe,
    path: str | Path,
    *,
    adapter_name: str = "mhn",
    weight: float = 1.0,
) -> None:
    """Load an ai-toolkit Chroma LoRA and FAIL LOUDLY if it does not apply."""
    state_dict = load_file(str(path))
    diffusers_sd = _convert_kohya_flux_lora_to_diffusers(
        _to_kohya_naming(state_dict)
    )
    pipe.load_lora_weights(diffusers_sd, adapter_name=adapter_name)
    active = pipe.get_active_adapters()
    if adapter_name not in active:
        raise RuntimeError(
            f"LoRA {Path(path).name} did not attach (active={active}); "
            "refusing to generate without identity."
        )
    pipe.set_adapters([adapter_name], adapter_weights=[weight])
    print(f"LoRA attached: {adapter_name} @ {weight}", flush=True)

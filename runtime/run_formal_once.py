from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from run_ir_once import validate_ir
from run_once import (
    ROOT,
    build_user_message,
    current_git_commit,
    get_field,
    get_usage_field,
    sha256_file,
    verify_standards,
)


DEFAULT_CONFIG_FILE = ROOT / "runtime" / "model_configs.json"
DEFAULT_CONFIG_KEY = "qwen3.8-max-0902-nonthinking-v1"
DEFAULT_REQUIREMENT = ROOT / "runtime" / "greenfield_requirement_002_formal.txt"
DEFAULT_RESULT_ROOT = ROOT / "results" / "formal_gf002_compare"

PROMPTS = {
    "direct_xml": ROOT / "runtime" / "prompts" / "formal_direct_dexpi_v0.1.txt",
    "ir": ROOT / "runtime" / "prompts" / "formal_engineering_ir_v0.1.txt",
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def resolve_from_root(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def load_model_config(path: Path, key: str) -> dict:
    configs = json.loads(path.read_text(encoding="utf-8"))
    if key not in configs:
        raise KeyError(f"Unknown model config: {key}")
    cfg = configs[key]
    required = {
        "provider",
        "model",
        "reasoning_effort",
        "temperature",
        "top_p",
        "top_k",
        "repetition_penalty",
        "seed",
        "max_completion_tokens",
        "n",
        "preserve_thinking",
    }
    missing = sorted(required - set(cfg))
    if missing:
        raise ValueError(f"Model config missing fields: {', '.join(missing)}")
    return cfg


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-shot formal Direct DEXPI or Engineering IR generation run."
    )
    parser.add_argument(
        "--case-id",
        default="UGS-GF-002",
        help="Formal benchmark case identifier.",
    )
    parser.add_argument(
        "--method",
        choices=("direct_xml", "ir"),
        required=True,
        help="Generation method to run exactly once.",
    )
    parser.add_argument(
        "--model-config-file",
        type=Path,
        default=DEFAULT_CONFIG_FILE,
    )
    parser.add_argument(
        "--model-config",
        default=DEFAULT_CONFIG_KEY,
    )
    parser.add_argument(
        "--requirement",
        type=Path,
        default=DEFAULT_REQUIREMENT,
        help="Shared engineering requirement used by both methods.",
    )
    parser.add_argument(
        "--system-prompt",
        type=Path,
        default=None,
        help="Optional externally stored prompt override for inspection/controlled replacement.",
    )
    parser.add_argument(
        "--result-root",
        type=Path,
        default=DEFAULT_RESULT_ROOT,
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")

    config_file = resolve_from_root(args.model_config_file)
    requirement_file = resolve_from_root(args.requirement)
    prompt_file = (
        resolve_from_root(args.system_prompt)
        if args.system_prompt is not None
        else PROMPTS[args.method]
    )
    result_root = resolve_from_root(args.result_root)

    cfg = load_model_config(config_file, args.model_config)
    system_prompt = prompt_file.read_text(encoding="utf-8")
    requirement = requirement_file.read_text(encoding="utf-8")

    standards = verify_standards() if args.method == "direct_xml" else None
    user_message = (
        build_user_message(requirement)
        if args.method == "direct_xml"
        else requirement
    )

    print(f"Method: {args.method}")
    print(f"Model config: {args.model_config}")
    print(f"Model snapshot: {cfg['model']}")
    print(f"Reasoning effort: {cfg['reasoning_effort']}")
    print(f"Temperature: {cfg['temperature']}")
    print(f"Top-p: {cfg['top_p']}")
    print(f"Top-k: {cfg['top_k']}")
    print(f"Repetition penalty: {cfg['repetition_penalty']}")
    print(f"Seed: {cfg['seed']}")
    print(f"Max completion tokens: {cfg['max_completion_tokens']}")
    print(f"Prompt: {prompt_file.relative_to(ROOT)}")
    print(f"Requirement: {requirement_file.relative_to(ROOT)}")
    print(f"System prompt text SHA-256: {sha256_text(system_prompt)}")
    print(f"Requirement text SHA-256: {sha256_text(requirement)}")
    print(f"User message text SHA-256: {sha256_text(user_message)}")
    print(f"User message characters: {len(user_message):,}")

    if args.dry_run:
        print("Dry run complete. No API call was made.")
        return

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is missing in the project-root .env.")

    base_url = os.getenv(
        "DASHSCOPE_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=1200.0)

    extra_body = {
        "reasoning_effort": cfg["reasoning_effort"],
        "top_k": cfg["top_k"],
        "repetition_penalty": cfg["repetition_penalty"],
        "preserve_thinking": cfg["preserve_thinking"],
    }

    start = time.perf_counter()
    completion = client.chat.completions.create(
        model=cfg["model"],
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=cfg["temperature"],
        top_p=cfg["top_p"],
        seed=cfg["seed"],
        max_completion_tokens=cfg["max_completion_tokens"],
        n=cfg["n"],
        stream=False,
        extra_body=extra_body,
    )
    latency_seconds = time.perf_counter() - start

    choice = completion.choices[0] if completion.choices else None
    content = get_field(get_field(choice, "message"), "content") or ""
    finish_reason = get_field(choice, "finish_reason")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = (
        result_root
        / args.method
        / f"{timestamp}_{str(cfg['model']).replace('/', '_')}"
    )
    output_dir.mkdir(parents=True, exist_ok=False)

    generated_name = "generated.xml" if args.method == "direct_xml" else "generated_ir.json"
    generated_file = output_dir / generated_name
    # Preserve the API-returned text bytes exactly as UTF-8; avoid platform newline conversion.
    generated_file.write_bytes(content.encode("utf-8"))

    if args.method == "ir":
        validation = validate_ir(content)
        (output_dir / "ir_validation.json").write_text(
            json.dumps(validation, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )

    usage = completion.usage
    metadata = {
        "timestamp_utc": timestamp,
        "case_id": args.case_id,
        "experiment": f"{args.case_id} direct XML vs Engineering IR formal comparison",
        "method": args.method,
        "provider": cfg["provider"],
        "endpoint_type": "DashScope OpenAI-compatible workspace endpoint; URL intentionally not recorded",
        "model_config_key": args.model_config,
        "model_requested": cfg["model"],
        "model_returned": completion.model,
        "generation_parameters": {
            "reasoning_effort": cfg["reasoning_effort"],
            "temperature": cfg["temperature"],
            "top_p": cfg["top_p"],
            "top_k": cfg["top_k"],
            "repetition_penalty": cfg["repetition_penalty"],
            "seed": cfg["seed"],
            "max_completion_tokens": cfg["max_completion_tokens"],
            "n": cfg["n"],
            "stream": False,
            "preserve_thinking": cfg["preserve_thinking"],
        },
        "finish_reason": finish_reason,
        "latency_seconds": latency_seconds,
        "model_config_file": str(config_file.relative_to(ROOT)),
        "model_config_file_sha256": sha256_file(config_file),
        "system_prompt_file": str(prompt_file.relative_to(ROOT)),
        "system_prompt_file_sha256": sha256_file(prompt_file),
        "system_prompt_text_sha256": sha256_text(system_prompt),
        "requirement_file": str(requirement_file.relative_to(ROOT)),
        "requirement_file_sha256": sha256_file(requirement_file),
        "requirement_text_sha256": sha256_text(requirement),
        "user_message_text_sha256": sha256_text(user_message),
        "generated_file": str(generated_file.relative_to(ROOT)),
        "generated_sha256": sha256_file(generated_file),
        "git_commit_hash": current_git_commit(),
        "python_version": platform.python_version(),
        "openai_sdk_version": importlib.metadata.version("openai"),
        "standards": standards,
        "usage": {
            "prompt_tokens": get_usage_field(usage, "prompt_tokens"),
            "completion_tokens": get_usage_field(usage, "completion_tokens"),
            "reasoning_tokens": get_usage_field(
                usage, "reasoning_tokens", "completion_tokens_details"
            ),
            "cached_tokens": get_usage_field(
                usage, "cached_tokens", "prompt_tokens_details"
            ),
            "total_tokens": get_usage_field(usage, "total_tokens"),
        },
    }
    (output_dir / "run.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )

    print(f"Latency: {latency_seconds:.2f} s")
    print(f"Finish reason: {finish_reason}")
    print(f"Saved: {generated_file}")
    if args.method == "ir":
        print(f"Saved: {output_dir / 'ir_validation.json'}")
    print(f"Saved: {output_dir / 'run.json'}")


if __name__ == "__main__":
    main()

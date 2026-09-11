from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]
STANDARD_DIR = ROOT / "standards" / "DEXPI_2.0.0"

STANDARD_FILES = [
    ("DEXPI_XML_Schema_RC_1.xsd", "0BD6568B7C52FD59AC4EF6D8547AB2B2AA890C009A3A1BFBC5D7CC18C53B36E6"),
    ("Core.xml", "D73D944D47A951FDB10FE796E7433936FA6D78C42DC686BD740918F5D21E6ABF"),
    ("Process.xml", "64A5AF8B2987EDC0186551CAA08FF9DA63F2B8EEF06663E322BE416B2981F4DA"),
]

DEFAULT_MODEL = "qwen3.8-max"
REASONING_EFFORT = "none"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def verify_standards() -> dict[str, str]:
    hashes: dict[str, str] = {}
    for filename, expected in STANDARD_FILES:
        path = STANDARD_DIR / filename
        if not path.is_file():
            raise FileNotFoundError(f"Missing frozen standard file: {path}")
        actual = sha256_file(path)
        if actual != expected:
            raise RuntimeError(
                f"SHA-256 mismatch for {filename}\n"
                f"expected: {expected}\n"
                f"actual:   {actual}"
            )
        hashes[filename] = actual
    return hashes


def read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def current_git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            check=False,
            text=True,
        )
    except OSError:
        return None

    if result.returncode != 0:
        return None
    commit = result.stdout.strip()
    return commit or None


def get_field(value: object, name: str) -> object | None:
    if isinstance(value, dict):
        return value.get(name)
    return getattr(value, name, None)


def get_usage_field(
    usage: object | None,
    name: str,
    *detail_names: str,
) -> object | None:
    value = get_field(usage, name)
    if value is not None:
        return value

    for detail_name in detail_names:
        value = get_field(get_field(usage, detail_name), name)
        if value is not None:
            return value
    return None


def build_user_message(requirement: str) -> str:
    xsd = read_utf8(STANDARD_DIR / "DEXPI_XML_Schema_RC_1.xsd")
    core = read_utf8(STANDARD_DIR / "Core.xml")
    process = read_utf8(STANDARD_DIR / "Process.xml")

    return "\n\n".join(
        [
            "=== OFFICIAL DEXPI 2.0.0 XSD ===\n" + xsd,
            "=== OFFICIAL DEXPI 2.0.0 CORE MODEL ===\n" + core,
            "=== OFFICIAL DEXPI 2.0.0 PROCESS MODEL ===\n" + process,
            "=== ENGINEERING DESIGN REQUIREMENT ===\n" + requirement,
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-shot standards-grounded DEXPI XML generation smoke test."
    )
    parser.add_argument(
        "--requirement",
        type=Path,
        default=ROOT / "runtime" / "smoke_requirement.txt",
        help="Path to the natural-language engineering requirement.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="DashScope model ID. Defaults to DASHSCOPE_MODEL or qwen3.8-max.",
    )
    parser.add_argument(
        "--system-prompt",
        type=Path,
        default=ROOT / "runtime" / "system_prompt.txt",
        help="Path to the system prompt file.",
    )
    parser.add_argument(
        "--result-group",
        default="smoke",
        help="Result directory group. Defaults to smoke.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Verify frozen files and build the prompt without calling the API.",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")

    standard_hashes = verify_standards()
    system_prompt_file = args.system_prompt
    if not system_prompt_file.is_absolute():
        system_prompt_file = ROOT / system_prompt_file
    system_prompt = read_utf8(system_prompt_file)
    requirement_file = args.requirement
    if not requirement_file.is_absolute():
        requirement_file = ROOT / requirement_file
    requirement = read_utf8(requirement_file)
    user_message = build_user_message(requirement)

    model = args.model or os.getenv("DASHSCOPE_MODEL") or DEFAULT_MODEL

    print("Frozen DEXPI files: OK")
    print(f"Model: {model}")
    print(f"System prompt characters: {len(system_prompt):,}")
    print(f"User message characters: {len(user_message):,}")
    print(f"User message UTF-8 bytes: {len(user_message.encode('utf-8')):,}")

    if args.dry_run:
        print("Dry run complete. No API call was made.")
        return

    api_key = os.getenv("DASHSCOPE_API_KEY")
    base_url = os.getenv(
        "DASHSCOPE_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    if not api_key:
        raise RuntimeError(
            "DASHSCOPE_API_KEY is missing. Put the real key in the project-root .env file."
        )

    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=1200.0,
    )

    start = time.perf_counter()
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        extra_body={"reasoning_effort": REASONING_EFFORT},
    )
    latency_seconds = time.perf_counter() - start

    choice = completion.choices[0] if completion.choices else None
    content = get_field(get_field(choice, "message"), "content") or ""
    finish_reason = get_field(choice, "finish_reason")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = (
        ROOT
        / "results"
        / args.result_group
        / f"{timestamp}_{model.replace('/', '_')}"
    )
    output_dir.mkdir(parents=True, exist_ok=False)

    # Preserve the model output exactly. Do not strip Markdown fences or repair XML.
    generated_xml_file = output_dir / "generated.xml"
    generated_xml_file.write_text(content, encoding="utf-8")
    generated_xml_sha256 = sha256_file(generated_xml_file)

    usage = completion.usage
    metadata = {
        "timestamp_utc": timestamp,
        "model_requested": model,
        "model_returned": completion.model,
        "reasoning_effort": REASONING_EFFORT,
        "finish_reason": finish_reason,
        "latency_seconds": latency_seconds,
        "requirement_file": str(requirement_file.relative_to(ROOT)),
        "system_prompt_file": str(system_prompt_file.relative_to(ROOT)),
        "system_prompt_sha256": sha256_file(system_prompt_file),
        "requirement_sha256": sha256_file(requirement_file),
        "generated_xml_sha256": generated_xml_sha256,
        "git_commit_hash": current_git_commit(),
        "standards": standard_hashes,
        "usage": {
            "prompt_tokens": get_usage_field(usage, "prompt_tokens"),
            "completion_tokens": get_usage_field(usage, "completion_tokens"),
            "reasoning_tokens": get_usage_field(
                usage,
                "reasoning_tokens",
                "completion_tokens_details",
            ),
            "text_tokens": get_usage_field(
                usage,
                "text_tokens",
                "completion_tokens_details",
            ),
            "cached_tokens": get_usage_field(
                usage,
                "cached_tokens",
                "prompt_tokens_details",
            ),
            "total_tokens": get_usage_field(usage, "total_tokens"),
        },
    }
    (output_dir / "run.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Latency: {latency_seconds:.2f} s")
    if usage:
        print(
            "Tokens: "
            f"input={getattr(usage, 'prompt_tokens', None)}, "
            f"output={getattr(usage, 'completion_tokens', None)}, "
            f"total={getattr(usage, 'total_tokens', None)}"
        )
    print(f"Saved: {generated_xml_file}")
    print(f"Saved: {output_dir / 'run.json'}")


if __name__ == "__main__":
    main()

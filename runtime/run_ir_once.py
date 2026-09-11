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
DEFAULT_MODEL = "qwen3.8-max"
REASONING_EFFORT = "none"
NODE_KINDS = {"source", "operation", "sink"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def git_commit() -> str | None:
    try:
        p = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        return p.stdout.strip() or None if p.returncode == 0 else None
    except OSError:
        return None


def validate_ir(text: str) -> dict:
    errors: list[str] = []
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return {
            "parseable": False,
            "valid": False,
            "errors": [
                f"JSON parse error at line {exc.lineno}, column {exc.colno}: {exc.msg}"
            ],
        }

    if not isinstance(data, dict):
        return {
            "parseable": True,
            "valid": False,
            "errors": ["Top-level JSON value must be an object."],
        }

    required_top = {"case_name", "scope", "material", "nodes", "streams"}
    missing = sorted(required_top - set(data))
    extra = sorted(set(data) - required_top)
    errors.extend(f"Missing top-level field: {key}" for key in missing)
    errors.extend(f"Unexpected top-level field: {key}" for key in extra)

    if not isinstance(data.get("case_name"), str):
        errors.append("case_name must be a string.")
    if data.get("scope") != "Design":
        errors.append('scope must be exactly "Design".')
    if not isinstance(data.get("material"), str):
        errors.append("material must be a string.")

    nodes = data.get("nodes")
    node_ids: set[str] = set()
    if not isinstance(nodes, list) or not nodes:
        errors.append("nodes must be a non-empty array.")
    else:
        for i, node in enumerate(nodes):
            if not isinstance(node, dict):
                errors.append(f"nodes[{i}] must be an object.")
                continue
            for key in ("id", "kind", "name"):
                if key not in node:
                    errors.append(f"nodes[{i}] missing field: {key}")

            node_id = node.get("id")
            if not isinstance(node_id, str) or not node_id:
                errors.append(f"nodes[{i}].id must be a non-empty string.")
            elif node_id in node_ids:
                errors.append(f"Duplicate node id: {node_id}")
            else:
                node_ids.add(node_id)

            kind = node.get("kind")
            if kind not in NODE_KINDS:
                errors.append(f"nodes[{i}].kind must be source, operation, or sink.")
            if not isinstance(node.get("name"), str):
                errors.append(f"nodes[{i}].name must be a string.")
            if kind == "operation" and not isinstance(node.get("operation"), str):
                errors.append(
                    f"nodes[{i}].operation must be a string for operation nodes."
                )
            if kind in {"source", "sink"} and "operation" in node:
                errors.append(
                    f"nodes[{i}].operation must be omitted for source/sink nodes."
                )

    streams = data.get("streams")
    stream_ids: set[str] = set()
    if not isinstance(streams, list) or not streams:
        errors.append("streams must be a non-empty array.")
    else:
        stream_fields = (
            "id",
            "from",
            "to",
            "flow",
            "flow_unit",
            "pressure_MPa",
            "temperature_C",
        )
        for i, stream in enumerate(streams):
            if not isinstance(stream, dict):
                errors.append(f"streams[{i}] must be an object.")
                continue
            for key in stream_fields:
                if key not in stream:
                    errors.append(f"streams[{i}] missing field: {key}")

            stream_id = stream.get("id")
            if not isinstance(stream_id, str) or not stream_id:
                errors.append(f"streams[{i}].id must be a non-empty string.")
            elif stream_id in stream_ids:
                errors.append(f"Duplicate stream id: {stream_id}")
            else:
                stream_ids.add(stream_id)

            source = stream.get("from")
            target = stream.get("to")
            if not isinstance(source, str) or source not in node_ids:
                errors.append(f"streams[{i}].from must reference a known node id.")
            if not isinstance(target, str) or target not in node_ids:
                errors.append(f"streams[{i}].to must reference a known node id.")
            if isinstance(source, str) and source == target:
                errors.append(f"streams[{i}] cannot connect a node to itself.")

            for key in ("flow", "pressure_MPa", "temperature_C"):
                value = stream.get(key)
                if value is not None and (
                    isinstance(value, bool) or not isinstance(value, (int, float))
                ):
                    errors.append(f"streams[{i}].{key} must be a number or null.")
            if not isinstance(stream.get("flow_unit"), str):
                errors.append(f"streams[{i}].flow_unit must be a string.")

    return {
        "parseable": True,
        "valid": not errors,
        "errors": errors,
        "node_count": len(nodes) if isinstance(nodes, list) else None,
        "stream_count": len(streams) if isinstance(streams, list) else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="One-shot greenfield Engineering IR generation pilot."
    )
    parser.add_argument(
        "--requirement",
        type=Path,
        default=ROOT / "runtime" / "greenfield_requirement_002_ir.txt",
    )
    parser.add_argument(
        "--system-prompt",
        type=Path,
        default=ROOT / "runtime" / "system_prompt_greenfield_ir.txt",
    )
    parser.add_argument("--model", default=None)
    parser.add_argument("--result-group", default="greenfield_ir_pilot")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")

    requirement_file = args.requirement
    if not requirement_file.is_absolute():
        requirement_file = ROOT / requirement_file
    system_prompt_file = args.system_prompt
    if not system_prompt_file.is_absolute():
        system_prompt_file = ROOT / system_prompt_file

    requirement = requirement_file.read_text(encoding="utf-8")
    system_prompt = system_prompt_file.read_text(encoding="utf-8")
    model = args.model or os.getenv("DASHSCOPE_MODEL") or DEFAULT_MODEL

    print(f"Model: {model}")
    print(f"System prompt characters: {len(system_prompt):,}")
    print(f"Requirement characters: {len(requirement):,}")

    if args.dry_run:
        print("Dry run complete. No API call was made.")
        return

    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("DASHSCOPE_API_KEY is missing in the project-root .env.")

    client = OpenAI(
        api_key=api_key,
        base_url=os.getenv(
            "DASHSCOPE_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        ),
        timeout=1200.0,
    )

    start = time.perf_counter()
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": requirement},
        ],
        extra_body={"reasoning_effort": REASONING_EFFORT},
    )
    latency_seconds = time.perf_counter() - start

    choice = completion.choices[0] if completion.choices else None
    content = choice.message.content if choice and choice.message.content else ""

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = (
        ROOT
        / "results"
        / args.result_group
        / f"{timestamp}_{model.replace('/', '_')}"
    )
    output_dir.mkdir(parents=True, exist_ok=False)

    generated_file = output_dir / "generated_ir.json"
    generated_file.write_text(content, encoding="utf-8")

    validation = validate_ir(content)
    (output_dir / "ir_validation.json").write_text(
        json.dumps(validation, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    usage = completion.usage
    usage_json = {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
    }
    details = getattr(usage, "completion_tokens_details", None)
    usage_json["reasoning_tokens"] = getattr(details, "reasoning_tokens", None)

    metadata = {
        "timestamp_utc": timestamp,
        "model_requested": model,
        "model_returned": completion.model,
        "reasoning_effort": REASONING_EFFORT,
        "finish_reason": choice.finish_reason if choice else None,
        "latency_seconds": latency_seconds,
        "requirement_file": str(requirement_file.relative_to(ROOT)),
        "system_prompt_file": str(system_prompt_file.relative_to(ROOT)),
        "requirement_sha256": sha256_file(requirement_file),
        "system_prompt_sha256": sha256_file(system_prompt_file),
        "generated_ir_sha256": sha256_file(generated_file),
        "git_commit_hash": git_commit(),
        "usage": usage_json,
    }
    (output_dir / "run.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Latency: {latency_seconds:.2f} s")
    print(f"IR valid: {validation['valid']}")
    print(f"Saved: {generated_file}")
    print(f"Saved: {output_dir / 'ir_validation.json'}")
    print(f"Saved: {output_dir / 'run.json'}")


if __name__ == "__main__":
    main()

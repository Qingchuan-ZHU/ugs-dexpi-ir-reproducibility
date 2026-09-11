from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from lxml import etree


ROOT = Path(__file__).resolve().parents[1]
XSD_FILE = ROOT / "standards" / "DEXPI_2.0.0" / "DEXPI_XML_Schema_RC_1.xsd"
EXPECTED_XSD_SHA256 = (
    "0BD6568B7C52FD59AC4EF6D8547AB2B2"
    "AA890C009A3A1BFBC5D7CC18C53B36E6"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def verify_frozen_xsd(path: Path) -> str:
    if not path.is_file():
        raise RuntimeError(f"Frozen DEXPI XSD is missing: {path}")

    actual = sha256_file(path)
    if actual != EXPECTED_XSD_SHA256:
        raise RuntimeError(
            "Frozen DEXPI XSD SHA-256 mismatch. Evaluation aborted.\n"
            f"expected: {EXPECTED_XSD_SHA256}\n"
            f"actual:   {actual}"
        )
    return actual


def load_frozen_schema(path: Path) -> etree.XMLSchema:
    xsd_parser = etree.XMLParser(
        load_dtd=True,
        no_network=True,
        recover=False,
        resolve_entities=True,
    )
    try:
        xsd_tree = etree.parse(str(path), xsd_parser)
        return etree.XMLSchema(xsd_tree)
    except Exception as error:
        raise RuntimeError(
            f"failed to parse or compile frozen DEXPI XSD: {error}"
        ) from error


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def error_log_entries(error_log: Any) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for entry in error_log:
        entries.append(
            {
                "domain": getattr(entry, "domain", None),
                "domain_name": getattr(entry, "domain_name", None),
                "type": getattr(entry, "type", None),
                "type_name": getattr(entry, "type_name", None),
                "level": getattr(entry, "level", None),
                "level_name": getattr(entry, "level_name", None),
                "line": getattr(entry, "line", None),
                "column": getattr(entry, "column", None),
                "message": getattr(entry, "message", str(entry)),
                "filename": getattr(entry, "filename", None),
                "path": getattr(entry, "path", None),
            }
        )
    return entries


def error_summaries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "line": entry.get("line"),
            "column": entry.get("column"),
            "message": entry.get("message"),
        }
        for entry in entries
    ]


def exception_summary(error: BaseException) -> dict[str, Any]:
    return {
        "line": getattr(error, "lineno", None),
        "column": getattr(error, "offset", None),
        "message": str(error),
    }


def write_result(output_file: Path, result: dict[str, Any]) -> str:
    serialized = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    with output_file.open("w", encoding="utf-8", newline="\n") as file:
        file.write(serialized)
    return serialized


def validate(xml_file: Path) -> tuple[dict[str, Any], Path]:
    xml_file = xml_file.resolve()
    xsd_file = XSD_FILE.resolve()
    output_file = xml_file.parent / "xsd_validation.json"

    # Evaluation infrastructure failures must not be counted as model failures.
    # Abort before producing an xsd_valid result if the frozen scoring schema
    # is missing, has drifted, or cannot be loaded.
    xsd_sha256 = verify_frozen_xsd(xsd_file)
    schema = load_frozen_schema(xsd_file)

    result: dict[str, Any] = {
        "xml_parseable": False,
        "xsd_valid": False,
        "error_count": 0,
        "errors": [],
        "xml_file": display_path(xml_file),
        "xsd_file": display_path(xsd_file),
        "xml_sha256": sha256_file(xml_file),
        "xsd_sha256": xsd_sha256,
        "validator_error_log": [],
    }

    xml_parser = etree.XMLParser(
        load_dtd=False,
        no_network=True,
        recover=False,
        resolve_entities=False,
    )
    try:
        xml_tree = etree.parse(str(xml_file), xml_parser)
    except (etree.XMLSyntaxError, OSError) as error:
        parser_entries = error_log_entries(xml_parser.error_log)
        result["errors"] = error_summaries(parser_entries) or [exception_summary(error)]
        result["error_count"] = len(result["errors"])
        return result, output_file

    result["xml_parseable"] = True

    result["xsd_valid"] = bool(schema.validate(xml_tree))
    validator_entries = error_log_entries(schema.error_log)
    result["validator_error_log"] = validator_entries
    if not result["xsd_valid"]:
        result["errors"] = error_summaries(validator_entries)
        result["error_count"] = len(result["errors"])

    return result, output_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate one generated DEXPI XML file against the frozen official XSD."
    )
    parser.add_argument("xml_file", type=Path, help="Path to generated.xml")
    args = parser.parse_args(argv)

    try:
        result, output_file = validate(args.xml_file)
    except RuntimeError as error:
        sys.stderr.write(f"Evaluator infrastructure error: {error}\n")
        return 2

    serialized = write_result(output_file, result)
    sys.stdout.write(serialized)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

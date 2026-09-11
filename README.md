# UGS DEXPI IR Reproducibility Package

This repository is a self-contained reproducibility snapshot for a small
three-case diagnostic comparison of two process-design generation method
bundles:

- Direct DEXPI generation;
- lightweight Engineering Intermediate Representation (IR) generation.

## Experimental structure

The package contains two generation methods for each of three cases:

- `UGS-GF-001`: single-pressure injection;
- `UGS-GF-002`: withdrawal and export;
- `UGS-GF-003`: dual-pressure injection.

All six formal conditions use one frozen model/configuration and one completed
generation per case-method condition.

| Case | Method | Representation | Engineering | Within-Method Outcome |
|---|---|---|---|---|
| GF-001 | Direct DEXPI | PASS | REJECT | FAIL |
| GF-001 | Engineering IR | PASS | WARN | WARN |
| GF-002 | Direct DEXPI | PASS | WARN | WARN |
| GF-002 | Engineering IR | PASS | REJECT | FAIL |
| GF-003 | Direct DEXPI | FAIL | WARN | FAIL |
| GF-003 | Engineering IR | PASS | ACCEPT | PASS |

## Interpretation boundary

This is a small diagnostic study, not a statistically representative
benchmark. Direct DEXPI and Engineering IR are method bundles, so the results
do not isolate XML versus JSON as a single independent variable. Engineering
IR structural validity is not engineering validity. XSD validity is the Direct
representation-validity gate and does not establish full DEXPI semantic
conformance. No deterministic IR-to-DEXPI conversion is evaluated. Engineering
feasibility labels are post-hoc qualitative reviews of the frozen outputs.

## Repository map

- `runtime/` contains the formal runner, retained support modules, formal
  prompts, formal requirements, and model configuration.
- `evaluation/` contains the Direct DEXPI XSD validator.
- `results/` contains the six frozen formal result sets.
- `docs/` contains the formal mini-benchmark engineering review.
- `standards/` contains the frozen DEXPI 2.0.0 reference files and notices.

## Reproduction

`runtime/run_formal_once.py` is the formal generation entry point. The exact
dry-run and hosted-rerun commands are documented in `REPRODUCIBILITY.md`.
The retained `run_once.py` and `run_ir_once.py` files provide shared helper
functionality for that formal path; they are not additional formal conditions.
Hosted reruns require the user's own API credentials, consume API calls, and
may not reproduce identical output bytes even with the same configuration and
seed.

Direct DEXPI generation depends on the frozen DEXPI reference files under
`standards/DEXPI_2.0.0/`. They are included in this package under their
upstream CC BY 4.0 license. If a package variant omits these third-party files,
obtain the exact files from the official source and place them at that path;
the runtime verifies their SHA-256 values before a Direct run.

## Frozen evidence

All raw generated XML/IR outputs, run metadata, and other validation records
are preserved byte-for-byte from the frozen source. One XSD validation record is
privacy-sanitized only to replace a machine-local absolute file URI with a
repository-relative path; its validation result and diagnostic content are
unchanged. The SHA-256 manifest records the distributed artifact hashes.

The manuscript, bibliography, manuscript figures, and other paper sources are
intentionally excluded from this package.

## License boundary

MIT applies to original project source code unless otherwise noted. The DEXPI
reference files are third-party material under CC BY 4.0 and are not covered by
the MIT license; see `THIRD_PARTY_NOTICES.md`.

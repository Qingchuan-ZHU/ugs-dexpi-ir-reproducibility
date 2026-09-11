# Reproducibility

This document describes the frozen formal inputs and the commands for
inspecting or rerunning the three-case comparison.

## Formal environment

- Python 3.10.11
- OpenAI SDK 2.54.0
- Fixed model snapshot: qwen3.8-max-0902
- Formal model configuration: runtime/model_configs.json
- reasoning_effort: none
- temperature: 0.7
- top_p: 0.8
- top_k: 20
- repetition_penalty: 1.0
- seed: 1234
- max_completion_tokens: 16384
- n: 1
- preserve_thinking: false
- stream: false

The seed is a reproducibility control. It is not a guarantee of bitwise
determinism for hosted inference.

## Formal inputs

Formal prompts:

- runtime/prompts/formal_direct_dexpi_v0.1.txt
- runtime/prompts/formal_engineering_ir_v0.1.txt

Formal requirements:

- runtime/greenfield_requirement_001_formal.txt
- runtime/greenfield_requirement_002_formal.txt
- runtime/greenfield_requirement_003_formal.txt

Formal runner:

- runtime/run_formal_once.py

The formal runner imports utility and validation functions from
runtime/run_once.py and runtime/run_ir_once.py. Those two files are retained
as legacy/support modules for the frozen formal runner; they are not separate
formal experiment conditions.

Validation:

- evaluation/validate_xsd.py validates one generated DEXPI XML file against the
  frozen official XSD.
- The minimal Engineering IR structural validator is in
  runtime/run_ir_once.py.

Formal results:

- results/formal_gf001_compare/
- results/formal_gf002_compare/
- results/formal_gf003_compare/

The formal outputs were preserved exactly as returned by the hosted model.
No repair, regeneration, or result-dependent retry was applied.

## Installation

~~~text
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
~~~

For a real hosted run, copy .env.example to .env and provide
DASHSCOPE_API_KEY locally. The real key is intentionally not included in this
repository. Formal experiments use the fixed snapshot in
runtime/model_configs.json.

## Dry runs

Dry runs verify the frozen files and construct the formal prompt without
calling the model API. The six formal conditions can be inspected with:

~~~text
python runtime/run_formal_once.py --case-id UGS-GF-001 --method direct_xml --requirement runtime/greenfield_requirement_001_formal.txt --result-root results/reruns/gf001_compare --dry-run
python runtime/run_formal_once.py --case-id UGS-GF-001 --method ir --requirement runtime/greenfield_requirement_001_formal.txt --result-root results/reruns/gf001_compare --dry-run
python runtime/run_formal_once.py --case-id UGS-GF-002 --method direct_xml --requirement runtime/greenfield_requirement_002_formal.txt --result-root results/reruns/gf002_compare --dry-run
python runtime/run_formal_once.py --case-id UGS-GF-002 --method ir --requirement runtime/greenfield_requirement_002_formal.txt --result-root results/reruns/gf002_compare --dry-run
python runtime/run_formal_once.py --case-id UGS-GF-003 --method direct_xml --requirement runtime/greenfield_requirement_003_formal.txt --result-root results/reruns/gf003_compare --dry-run
python runtime/run_formal_once.py --case-id UGS-GF-003 --method ir --requirement runtime/greenfield_requirement_003_formal.txt --result-root results/reruns/gf003_compare --dry-run
~~~

These commands do not call the hosted model and do not reproduce the frozen
raw results.

## Real reruns

Remove the dry-run flag from the corresponding command above. For example:

~~~text
python runtime/run_formal_once.py --case-id UGS-GF-001 --method direct_xml --requirement runtime/greenfield_requirement_001_formal.txt --result-root results/reruns/gf001_compare
python runtime/run_formal_once.py --case-id UGS-GF-001 --method ir --requirement runtime/greenfield_requirement_001_formal.txt --result-root results/reruns/gf001_compare
python runtime/run_formal_once.py --case-id UGS-GF-002 --method direct_xml --requirement runtime/greenfield_requirement_002_formal.txt --result-root results/reruns/gf002_compare
python runtime/run_formal_once.py --case-id UGS-GF-002 --method ir --requirement runtime/greenfield_requirement_002_formal.txt --result-root results/reruns/gf002_compare
python runtime/run_formal_once.py --case-id UGS-GF-003 --method direct_xml --requirement runtime/greenfield_requirement_003_formal.txt --result-root results/reruns/gf003_compare
python runtime/run_formal_once.py --case-id UGS-GF-003 --method ir --requirement runtime/greenfield_requirement_003_formal.txt --result-root results/reruns/gf003_compare
~~~

Each real rerun consumes API calls and may not reproduce identical output
bytes, even with the same seed and configuration. A rerun is not a replacement
for the preserved formal evidence.

## XSD validation example

The validator writes xsd_validation.json beside the XML file. To keep the
preserved formal evidence unchanged, first copy one frozen generated.xml into
the isolated rerun validation path:

~~~text
New-Item -ItemType Directory -Force results/reruns/validation_example
Copy-Item results/formal_gf001_compare/direct_xml/20260910T105347Z_qwen3.8-max-0902/generated.xml results/reruns/validation_example/generated.xml
python evaluation/validate_xsd.py results/reruns/validation_example/generated.xml
~~~

The directories below are preserved formal evidence and must not be modified
by reproduction commands:

- results/formal_gf001_compare/
- results/formal_gf002_compare/
- results/formal_gf003_compare/

The validator uses the frozen XSD under standards/DEXPI_2.0.0. The result
record is an evaluation artifact and should be interpreted together with the
engineering review; XSD validity alone is not engineering validation.

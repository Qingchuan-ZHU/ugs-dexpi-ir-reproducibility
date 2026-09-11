# UGS Formal Mini-Benchmark Review v0.1

## Scope and evidence boundary

This document is a post-hoc review of the six formal paired results for:

- UGS-GF-001
- UGS-GF-002
- UGS-GF-003

The raw-result freeze for UGS-GF-001 and UGS-GF-003 is commit
`09d641133dccddbc2a901af63722c75694330357`.

The formal-generation provenance recorded in the UGS-GF-001 and UGS-GF-003
`run.json` files is commit
`3f646644e6e9d0d41bec3b27843f3e1b41fd9f15`.

UGS-GF-002 remains the previously frozen formal result. Its recorded
generation commit is `4e0bf753bf37a3bf97869e718e8a55a45bf69acc`. GF-002 was
not rerun or modified.

This review does not modify any raw generated output, `run.json`, validation
JSON, prompt, requirement, model configuration, runner, or DEXPI reference.

## Evaluation contract

The review keeps three dimensions separate.

### Representation Validity

For Direct DEXPI:

- `PASS` means the XML is parseable and DEXPI XSD-valid.
- `FAIL` means XML parsing or XSD validation fails.

For Engineering IR:

- `PASS` means JSON is parseable and valid under the minimal IR structural
  validator.
- `FAIL` means either condition fails.

IR `PASS` means only `structurally valid under the minimal IR validator`. It
does not mean engineering-valid or physically-valid.

### Engineering Feasibility

- `ACCEPT`
- `WARN`
- `REJECT`

`WARN` denotes an otherwise acceptable engineering result with a non-fatal
concern.

This dimension evaluates process topology, flow/pressure/temperature states,
operation/state consistency, and the stated engineering boundary conditions.

### End-to-End Outcome

- `PASS`
- `WARN`
- `FAIL`

`WARN` denotes an otherwise acceptable result with a non-fatal qualification.
This dimension evaluates whether the complete requested representation and
engineering result is acceptable for the method. A Direct result that is
engineering-plausible but fails the required DEXPI representation is not an
end-to-end pass.

## Raw-result provenance

All six formal generations used the fixed model and parameters below:

```text
model_requested/model_returned = qwen3.8-max-0902
model_config_key = qwen3.8-max-0902-nonthinking-v1
reasoning_effort = none
temperature = 0.7
top_p = 0.8
top_k = 20
repetition_penalty = 1.0
seed = 1234
max_completion_tokens = 16384
n = 1
stream = false
preserve_thinking = false
```

| Case | Method | Timestamp | Generation commit | Requirement text SHA-256 | Generated SHA-256 | Finish | Latency (s) |
|---|---|---|---|---|---|---|---:|
| GF-001 | Direct DEXPI | 20260910T105347Z | `3f646644...` | `DC2A93CBCDEE67DAD5F87000E4EDB55F135F1E94BCFE5DA0B943F8A0FF25BA9E` | `4BE906EFA1FFF48B92B192B2308655039CD992C1461E93496116ED79F9EC0427` | stop | 168.13 |
| GF-001 | Engineering IR | 20260910T105416Z | `3f646644...` | `DC2A93CBCDEE67DAD5F87000E4EDB55F135F1E94BCFE5DA0B943F8A0FF25BA9E` | `F3290F462FE4F02156921DFBA12CFD9503F3C9B339E64542133E5C373B75A51F` | stop | 11.45 |
| GF-002 | Direct DEXPI | 20260910T102502Z | `4e0bf753...` | `FAB1BADE47AC88D1D9A7AF1E04AA6E24A922859D1033FCD6CCEB081C397C9086` | `96560A0EEDDCBAAE02FB3AD8A3E2F6F0A01FA95502513A94CA24E40DA417FD2D` | stop | 87.71 |
| GF-002 | Engineering IR | 20260910T102523Z | `4e0bf753...` | `FAB1BADE47AC88D1D9A7AF1E04AA6E24A922859D1033FCD6CCEB081C397C9086` | `5F20C602D0D9877775B2056B2735C9D48409958A2D242DE6E70ACEB287197629` | stop | 10.03 |
| GF-003 | Direct DEXPI | 20260910T105650Z | `3f646644...` | `79FDA6CC5C0BAABE55E509D03DCEC42BEA8B83677FC272A9424ABBA1D7FD836E` | `5D59C1BC6CFD019F3AAB17F52D50F987BB8E2D4726FA13FD0B7BAE331FDE16C0` | stop | 146.78 |
| GF-003 | Engineering IR | 20260910T105723Z | `3f646644...` | `79FDA6CC5C0BAABE55E509D03DCEC42BEA8B83677FC272A9424ABBA1D7FD836E` | `0C918FEF21431A529B180D7B47C6F127056AFD741832255D955CB3AC208E6F9C` | stop | 21.09 |

The Direct prompt file SHA-256 is
`6B8ACD5600576764DC614749AE3C29A4924AFB7D9F0D48F72AF7C216DCA9CB36` and
the Engineering IR prompt file SHA-256 is
`829045BBB7FAD47CC688A5CB0BCCEECB76D4746DFABB46ED5196EEEA0F094446`.

The four UGS-GF-001/003 generated-file hashes were recomputed from disk and
matched their corresponding `run.json` values. The Direct and IR requirement
text hashes match within each case.

## Case reviews

### UGS-GF-001 Direct DEXPI

Raw evidence:

- `results/formal_gf001_compare/direct_xml/20260910T105347Z_qwen3.8-max-0902/generated.xml`
- `results/formal_gf001_compare/direct_xml/20260910T105347Z_qwen3.8-max-0902/run.json`
- `results/formal_gf001_compare/direct_xml/20260910T105347Z_qwen3.8-max-0902/xsd_validation.json`

Representation Validity: **PASS**.

The XML is parseable, and `xsd_validation.json` reports `xsd_valid = true`
with zero errors. This does not resolve semantic or engineering defects.

Engineering Feasibility: **REJECT**.

The main represented sequence is metering/regulation, three compressor
objects, interstage cooling, aftercooling, an injection manifold, and two
well sinks. The raw XML has the following defects:

- No explicit `Source` process object is present.
- `str_01` has `Source = port_meter_in` and `Target = port_meter_in`, which is
  a feed self-loop rather than a source-to-meter connection.
- Most main-process streams have no flow value. The only feed flow is `8.1
  m3/s`, not an explicitly stated `700,000 standard_m3/day` flow.
- The two post-manifold well branches have no flow values.
- The stream into the aftercooler is `35 MPa / 48 °C`, while the stream out is
  `35 MPa / 55 °C`. The object is a cooling operation but the recorded state
  increases in temperature.
- The second compression stage has already reached approximately `35 MPa`,
  while the remaining third compressor does not produce a clear further
  pressure increase. This is an additional process-logic concern.

The rejection is based on the obvious operation/state contradiction and the
main-flow topology defect, not on a preference for a particular human design.

End-to-End Outcome: **FAIL**.

### UGS-GF-001 Engineering IR

Raw evidence:

- `results/formal_gf001_compare/ir/20260910T105416Z_qwen3.8-max-0902/generated_ir.json`
- `results/formal_gf001_compare/ir/20260910T105416Z_qwen3.8-max-0902/ir_validation.json`
- `results/formal_gf001_compare/ir/20260910T105416Z_qwen3.8-max-0902/run.json`

Representation Validity: **PASS**.

The JSON is parseable and the minimal validator reports `valid = true`, with
8 nodes and 7 streams. This is a structural result only.

Engineering Feasibility: **WARN**.

The topology is:

```text
Regional Transmission Network
→ Inlet Metering and Filtration
→ First Stage Compression
→ Interstage Cooling
→ Second Stage Compression
→ Aftercooling
→ Injection Metering and Manifold
→ Underground Gas Storage Wells
```

All seven streams carry `700,000 standard_m3/day`. Compression increases
pressure, cooling decreases temperature, and the final state is
approximately `35 MPa / 50 °C`, satisfying the stated boundary.

The qualification is the small unexplained state change after aftercooling:

```text
35.0 MPa → 34.8 MPa → 35.0 MPa
                    metering/manifolding
```

The `34.8 → 35.0 MPa` increase has no explicit compression or other pressure-
raising operation. It is a minor operation/state consistency issue, not a key
boundary failure.

End-to-End Outcome: **WARN**.

### UGS-GF-002 Direct DEXPI

Raw evidence:

- `results/formal_gf002_compare/direct_xml/20260910T102502Z_qwen3.8-max-0902/generated.xml`
- `results/formal_gf002_compare/direct_xml/20260910T102502Z_qwen3.8-max-0902/run.json`
- `results/formal_gf002_compare/direct_xml/20260910T102502Z_qwen3.8-max-0902/xsd_validation.json`

Representation Validity: **PASS**.

The XML is parseable and XSD-valid with zero validation errors.

Engineering Feasibility: **WARN**.

The main material topology is:

```text
Withdrawal Well Manifold
→ Inlet ESDV
→ Inlet Filter Separator
→ Pressure Control Valve
→ Export Gas Cooler
→ Export Pipeline
```

The `FT-01` Export Flow Meter object exists, but it has no material ports and
is not connected to the main material-stream topology. It must therefore not
be counted as a connected process step.

The process correctly represents withdrawal/export, pressure reduction to
approximately `7 MPa`, and cooling from `48 °C` to `35 °C`. The final
connected stream records `450,000 m3/day` at approximately `7 MPa / 35 °C`.
The numerical flow value matches the specified capacity, but the standard-
volume basis is not explicitly encoded in that connected stream. The
unconnected `FT-01` object separately records `450000 Sm3/d`, but it is not a
connected material-stream step.

Qualifications:

- The connected final stream does not explicitly encode the required standard-
  volume basis.
- The pressure-letdown stream records approximately `25 °C → 48 °C`. This is
  a strong thermodynamic plausibility concern or unsupported intermediate
  state, but the available requirement does not provide composition, EOS, or
  Joule–Thomson data. It is not classified as an unconditional mathematical
  impossibility.
- Intermediate stream flow metadata is sparse.
- The filter separator is a model choice rather than an explicit hard
  requirement.

The `25 °C → 48 °C` concern is not treated as the same category as the GF-002
IR error `12 °C → 35 °C` across an explicitly named cooling operation.

End-to-End Outcome: **WARN**.

### UGS-GF-002 Engineering IR

Raw evidence:

- `results/formal_gf002_compare/ir/20260910T102523Z_qwen3.8-max-0902/generated_ir.json`
- `results/formal_gf002_compare/ir/20260910T102523Z_qwen3.8-max-0902/ir_validation.json`
- `results/formal_gf002_compare/ir/20260910T102523Z_qwen3.8-max-0902/run.json`

Representation Validity: **PASS**.

The JSON is parseable and valid under the minimal IR validator, with 6 nodes
and 5 streams.

Engineering Feasibility: **REJECT**.

The flow remains complete at `450,000 standard_m3/day`; the final pressure is
`6.8 MPa` and the final temperature is `35 °C`. The pressure-letdown change
from `25 °C` to `12 °C` is not by itself the rejection reason.

The explicit contradiction is:

```text
Pressure Control Valve outlet: 7.0 MPa / 12 °C
Export Gas Cooler outlet:      6.9 MPa / 35 °C
```

The operation is labeled `cooling`, but its temperature increases from
`12 °C` to `35 °C`. This is an obvious operation/state contradiction that does
not require EOS or property data to identify.

End-to-End Outcome: **FAIL**.

### UGS-GF-003 Direct DEXPI

Raw evidence:

- `results/formal_gf003_compare/direct_xml/20260910T105650Z_qwen3.8-max-0902/generated.xml`
- `results/formal_gf003_compare/direct_xml/20260910T105650Z_qwen3.8-max-0902/run.json`
- `results/formal_gf003_compare/direct_xml/20260910T105650Z_qwen3.8-max-0902/xsd_validation.json`

Representation Validity: **FAIL**.

The XML is parseable but not XSD-valid. The raw validator reports:

```text
line 87
Element 'Data': This element is not expected.
Expected is one of:
AggregatedDataValue, DataReference, Boolean, DateTime, Double, Integer, String, Undefined

path:
/Model/Object/Components[5]/Object/Data[3]/AggregatedDataValue/Data/Data[1]
```

Engineering Feasibility: **WARN**.

The engineering topology is:

```text
Regional Transmission Network
→ Feed Header Splitter
├─ Train A Compressor → Train A Aftercooler → Injection Well Group A
└─ Train B Compressor → Train B Aftercooler → Injection Well Group B
```

The raw stream states record:

- Total feed: numerical flow `900,000 m3/day`, `8.5 MPa`, `15 °C`.
- Group A: numerical flow `300,000 m3/day`, final `20 MPa / 50 °C`.
- Group B: numerical flow `600,000 m3/day`, final `30 MPa / 50 °C`.
- Numerical flow balance: `300,000 + 600,000 = 900,000`.
- The standard-volume basis required by the case is not explicitly encoded.
- Both branches are present simultaneously.
- Compression raises pressure and cooling lowers temperature.
- No obvious operation/state contradiction is present.

The topology, pressure, temperature, and numerical flow split are acceptable,
but the required flow basis is incompletely represented. This produces a WARN
in Engineering Feasibility. The independent XSD failure belongs to
Representation Validity.

End-to-End Outcome: **FAIL** because the required Direct DEXPI representation
is not XSD-valid.

### UGS-GF-003 Engineering IR

Raw evidence:

- `results/formal_gf003_compare/ir/20260910T105723Z_qwen3.8-max-0902/generated_ir.json`
- `results/formal_gf003_compare/ir/20260910T105723Z_qwen3.8-max-0902/ir_validation.json`
- `results/formal_gf003_compare/ir/20260910T105723Z_qwen3.8-max-0902/run.json`

Representation Validity: **PASS**.

The JSON is parseable and valid under the minimal IR validator, with 15 nodes
and 14 streams.

Engineering Feasibility: **ACCEPT**.

The topology contains source, metering, splitter, two independent compressor/
cooling trains, and two sinks. The flow balance is:

```text
900,000 → 300,000 + 600,000 standard_m3/day
```

The final states are:

- Group A: `300,000 standard_m3/day`, `20 MPa`, `40 °C`.
- Group B: `600,000 standard_m3/day`, `30 MPa`, `40 °C`.

All compression steps raise pressure, all cooling steps lower temperature, and
the simultaneous dual-pressure requirement is represented without an obvious
operation/state contradiction.

End-to-End Outcome: **PASS**.

## Unified result table

| Case | Method | Representation Validity | Engineering Feasibility | End-to-End |
|---|---|---|---|---|
| GF-001 | Direct DEXPI | PASS | REJECT | FAIL |
| GF-001 | Engineering IR | PASS | WARN | WARN |
| GF-002 | Direct DEXPI | PASS | WARN | WARN |
| GF-002 | Engineering IR | PASS | REJECT | FAIL |
| GF-003 | Direct DEXPI | FAIL | WARN | FAIL |
| GF-003 | Engineering IR | PASS | ACCEPT | PASS |

## Token and latency comparison

| Case | Method | Prompt tokens | Completion tokens | Latency (s) |
|---|---|---:|---:|---:|
| GF-001 | Direct DEXPI | 121,839 | 10,573 | 168.13 |
| GF-001 | Engineering IR | 617 | 590 | 11.45 |
| GF-002 | Direct DEXPI | 121,881 | 6,655 | 87.71 |
| GF-002 | Engineering IR | 659 | 434 | 10.03 |
| GF-003 | Direct DEXPI | 121,921 | 9,467 | 146.78 |
| GF-003 | Engineering IR | 699 | 1,078 | 21.09 |

The IR prompt burden is dramatically lower across all three cases. The raw
latency values are reported descriptively; latency ratios are not treated as
strict model-performance conclusions because server load, caching, and
backend scheduling can affect latency.

## Conclusions and limits

The Direct DEXPI failures have two distinct forms:

1. Engineering reasoning/state-consistency failure, exemplified by GF-001.
2. DEXPI serialization failure, exemplified by GF-003.

Engineering IR substantially reduces representation burden and separates
engineering semantics from DEXPI serialization. In these three formal cases,
all three IR outputs passed the minimal structural validator.

IR validity does not guarantee engineering correctness. GF-002 is the direct
counterexample: a structurally valid IR with complete flow representation and
apparently correct final boundary conditions still contains an
engineering-inconsistent cooling state.

The supported conclusion is therefore:

> The structured IR substantially reduces representation burden and separates
> engineering semantics from DEXPI serialization, but engineering consistency
> remains a model-level challenge.

This is a formal three-case mini-benchmark / diagnostic comparison, not a
statistically representative benchmark. No universal claim that IR improves
engineering correctness is supported by these three cases.
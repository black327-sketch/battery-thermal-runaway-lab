# Fact Based Logic Report

## Experimental Facts Mapped Into Logic
- Literature-device mode requires SOC selection, prismatic LFP cell placement, T1/T2/T3 thermocouples, voltage leads, pressure sensor check, chamber closure, vacuum, and nitrogen fill before heating.
- Four sampling nodes are enforced as teaching logic:
  - first sampling: T2 reaches 100 ?C;
  - second sampling: safety valve venting;
  - third sampling: temperature peak / most intense reaction stage;
  - fourth sampling: pressure stable / reaction nearing completion.
- 0%SOC venting is allowed as a teaching node but is blocked from being forced into thermal-runaway peak logic.
- GC requires completed sampling.
- LFL/risk evaluation requires GC and gas volume data.
- Risk ratio remains `R = C / LFL_mix` and is explicitly labelled as a teaching model.

## Warning Rationale
`assessment_engine.py` now records these fields for failed actions:
- category
- reason
- impact
- correct_action
- basis

Covered categories include process error, data missing, safety-boundary error, sampling-node error, risk-evaluation error, and report-generation condition missing.

## Risk Boundary
`risk_model.py` now returns levels such as `????????`, `???????`, `?????????`, and `????????`, plus `model_boundary` text. This prevents risk output from being read as real engineering or emergency guidance.

## Tests
- Assessment tests verify fact-based warning fields.
- Risk-model tests verify the teaching-model labels.
- Literature state test verifies 0%SOC does not force thermal-runaway peak progression.
- Full test suite with backup ignored: `221 passed`.

## Authority Boundaries Used
The iteration used the project's encoded reference facts and CSV/documentation structure as the primary source. No new external facts or standards clauses were invented. Standards such as UL 9540A remain treated only as general safety-evaluation context if referenced elsewhere.

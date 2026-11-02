# Stage 4 routing comparison

## Configuration used

- Authentication mode: API key (value withheld)
- Foundry endpoint: configured (value withheld)
- Lightweight deployment: `gpt-5-mini`
- Frontier deployment: `gpt-5.4`
- Managed router deployment: `agent-router-managed`
- System-one threshold: 0.85
- Human-review threshold: below 0.60

## Summary

| Strategy | Route accuracy | Average latency (ms) | Overrides | Failures |
| --- | ---: | ---: | ---: | ---: |
| option_a_explicit | 92% | 5398 | 9 | 0 |
| option_b_managed | 92% | 4226 | 9 | 0 |
| option_c_hybrid | 100% | 7432 | 9 | 0 |

## Managed-router model selections

- `gpt-5-mini-2025-08-07`
- `gpt-5.4-2026-03-05`

## Safety-rule overrides

- `invalid_classifier_output`
- `investigation_or_ambiguity`
- `low_confidence`
- `state_change_or_approval`

## Failures

- None

## Safe route differences

- Option A escalated `ambiguous-002` to human review after invalid classifier output.
- Option B escalated `ambiguous-002` to human review because confidence was below 0.60.

## Initial recommendation

Use Option C (hybrid) as the initial candidate: it achieved 100% route accuracy in
this limited synthetic comparison while retaining local safety-policy enforcement.
It had the highest average latency, so retain Option A as the audit-friendly
baseline and re-evaluate both with a larger production-like benchmark. This pass
does not estimate cost.

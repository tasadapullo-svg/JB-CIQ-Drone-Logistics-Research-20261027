# G0 independent reproduction and difference report

## Gate

- Input registry: 18 key artifacts, missing 0.
- Historical S11 ZIP: PASS_CONDITIONAL; CRC bad member: None.
- ZIP manifest mismatch: 3 members, all pyc-only=True.
- S11 numerical reproduction: PASS.
- Golden road/event-clock cases: PASS,PASS.
- Historical implicit M1 station nodes: 11 (A01,A02,A03,A09,A_N05,A_N07,B06,B07,C02,C04,C21); all in frozen V5=True.

## Independent recalculation

The 56,342 flights are the sum of strict (7,389) and relaxed (48,953) spatial-weather scenarios. They are not strict-only flights. Each seed contains 2,754 orders across 153 days and represents one five-month simulation replicate.

## G1 decision

GO to code repair and tests. The 11-node historical station set is reproducible from S10 and belongs to frozen V5, so it can be used as a conditional project whitelist. Real site access/permission remains HOLD. No S11 result is promoted to the S11B baseline until P0-01 through P0-06 are repaired and rerun.

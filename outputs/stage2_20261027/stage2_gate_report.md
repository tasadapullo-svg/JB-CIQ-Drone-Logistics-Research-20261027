# Stage 2质量门槛报告

全量主实验：**不放行**。

| Gate | 状态 | 证据 | 例外/阻塞 | 下一步 |
|---|---|---|---|---|
| G1_DATA_LINEAGE | BLOCKED | 30-seed snapshot verified; V5.5 source and V5.6 generator absent | cannot reproduce transformation from frozen source | recover exact file/hash and generator |
| G2_OD_STATUS | PASS | 128/128 attributed; 37 exceptions classified; 37 diagnostic candidates | formal repairs remain zero | manually validate access and direction for candidates |
| G3_ROAD_INTERNAL | BLOCKED | no negative road time; edge-aware diagnostic complete | turn restrictions and legal boundary unverified | parse restrictions and validate legal boundary |
| G4_CIQ_SEPARATION | PASS | road and CIQ fields separated; 128 inland ODs marked CIQ not applicable | cross-border OD set not yet defined | retain separate event components |
| G5_EXTERNAL_CALIBRATION | BLOCKED | official sources reviewed; no matched historical wait-minute series | MAE/MdAE/SMAPE unavailable | obtain corridor-direction-hour observations or retain scenarios |
| G6_STATION_OPERATIONS | BLOCKED | diagnostic state fields created | replenishment/queue/charging/fallback model absent | freeze sourced operational parameters and implement |
| G7_DRONE_RESTRICTIONS | BLOCKED | weather and geometric screens remain separate | aircraft/energy/reserve/permission evidence absent | freeze sourced aircraft and regulatory inputs |
| G8_MODE_PARITY | PASS | same existing orders retained once in each M0/M1/M2 diagnostic row | all results NOT_EVALUABLE | rerun after G3/G5/G6/G7 pass |
| G9_COST_EMISSIONS | BLOCKED | schema reserved and null | functional unit/lifecycle and factors absent | freeze sourced accounting boundary |
| G10_REPRODUCIBILITY | PASS | read-only inputs hashed; deterministic scripts/tests/manifest included | no git repository at root | preserve ZIP and SHA256 |

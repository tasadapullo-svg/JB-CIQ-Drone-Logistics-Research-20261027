# S11 Complete Reproduction Guide

Run from `C:\Users\DELL\Desktop\CIQ 无人机物流 SCI 研_20261026` with Python 3.14.3.

1. Verify frozen inputs with `G11_0_PRECHECK/code/run_g11_0.py`.
2. Execute `G11_1_DYNAMIC_WEATHER/code/run_s11_corrective_chunk.py` in four chunks for the 24 h main run.
3. Repeat with environment variable `S11_DUTY_HOURS=8`, `12`, and `30` plus `--summary-only`.
4. Run `shared/postprocess_s11.py`.
5. Run `G11_4_DUTY_ROAD/code/audit_hour_cache.py`.
6. Run `shared/finalize_s11.py`.

Historical S07–S10 inputs are referenced by SHA-256 and are not duplicated in every ZIP. A genuinely independent rerun therefore also requires the frozen directories `output_S07_S08_Codex_20261030` and `output_S08A_S09_S10_Codex_20261030/RUN_20261030_01` listed in the input registry.

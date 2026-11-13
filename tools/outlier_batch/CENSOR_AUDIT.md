# Signed score and censoring audit — 2026-11-02

Read-only audit of all 210 CSVs under participant 01–30 `processed_csv` directories. No source files, metadata or values were changed.

## Evidence and counts

Eligibility here is channel-specific: finite value, channel status `scored`, channel valid `1`. Historical review flags are ignored after the user's manual review. Global `score_complete` is not used because failure of the other component should not exclude a valid component.

| Channel | Eligible observations | Left censored | Right censored | Baseline / training / test censored |
|---|---:|---:|---:|---|
| Angle | 5182 | 0 | 0 | 0 / 0 / 0 |
| Strength | 4960 | 0 | 269 | 50 / 158 / 61 |

All 269 strength observations satisfy both `abs(strength_value) ≈ strength_maximum` (allowing six-decimal rounding) and `abs(strength_uncapped) > strength_maximum`. All have `strength_method=motion_model` and `strength_stop_reason=predicted_stop_after_crossing`. These are documented score-clipping events on predicted stopping scores, not 269 independently observed natural stopping locations.

Example: `02/processed_csv/02_01_baseline_both_010shots.csv`, shot 2: value `1.002894`, maximum `1.0028942726167258`, uncapped `5.210056`. Source `MOLT4_results/processing_info.json` also records the capped scoring version and per-file strength maximum.

## Interpretation

- `process_experiment_csv.py` creates signed `strength_value` using target-line geometry and signed `angle_value` using the center line. It leaves upstream maximum/uncapped columns unchanged. Sign therefore comes from the signed value, not the unsigned uncapped column.
- The upstream uncapped strength column is a motion-model prediction. Using it as an exact measured natural stopping value would overstate the evidence. The main likelihood uses the clipped score as a right-bound observation; the likelihood contribution is the Student-t survival probability above the exact recorded maximum.
- This is censoring of the score/predicted-performance measurement. It does not by itself identify the distribution of true physical stopping errors or model prediction uncertainty. The latter requires an additional measurement-error model and calibration validation.
- `angle_maximum` is 90 degrees in these files. No eligible angle value meets the joint clipping evidence; large angles alone must not be marked censored.
- Equality to a maximum alone is insufficient evidence. Missing metadata yields code 0 (no demonstrated clipping), not proof of an unbounded measurement.
- `MOLT4_results/README.md` states that unconfirmed natural stops were not scored and old estimates are for audit only. The signed processing script fills some previously empty values, but does not turn `unresolved` status into `scored`; downstream valid-status masking remains necessary.
- Enforcing global `score_complete=1` would unnecessarily remove 136 otherwise valid scored angle measurements because another component failed; this audit keeps channels independent.

## Shared helper and validation

`censoring.py` exports `censor_codes(df, channel)` (aligned -1/0/+1 array) and `censor_values(df, channel)` (aligned numeric values with demonstrated caps replaced by exact signed maxima). Neither function mutates its input. Caller applies its channel eligibility mask.

`python -m unittest discover -s tools/outlier_batch -p test_censoring.py`: 2 tests passed, covering signed clipping, exact boundaries, rounding, missing metadata, non-clipped large values, and input preservation.

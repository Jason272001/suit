# Accuracy and the future scanning booth

## Implemented, and what it establishes

Reference mode estimates scale from a known vertical segment in the same image:
`height_cm = (floor_y - crown_y) / (reference_bottom_y - reference_top_y) * reference_length_cm`.
An entered height is optional and does not change this scale. A discrepancy of
one inch or more blocks measurement results until the setup/input is checked. One inch
is an input-conflict threshold, not an accuracy tolerance or a confidence bound.
The application rejects inadequate reference size, visible reference tilt,
clipped or low-visibility landmarks, and obvious leaning/side views.

This is an experimental planar scale estimate. Users mark both reference ends,
head top, and floor. A flat reference must be vertical at the person's depth; a
reference held toward the camera changes scale. Perspective, lens distortion,
shoes/hair, posture, body depth, erroneous paper size and user marks still cause
error. The software cannot verify depth alignment from this photo. A checkbox
records user confirmation, not a sensor verification. No perfect scan is claimed.
All downloadable records retain calibration evidence and `production_ready:false`.
Weight is not inferred or required for this prototype's landmark estimates.

## Validation before training or production

1. Obtain explicit consent for collecting scans or using them for model training.
   Current app sessions are not retained or automatically collected for training.
2. Independently measure barefoot standing height with a stadiometer, or a level
   head marker and checked wall/tape. Record the instrument/method separately;
   do not treat an entered guess, marker length, or model output as ground truth.
3. Compare repeated scans across devices, light, distance, clothing, posture,
   body shapes and heights. Record calibration setup, reference length, anonymous
   subject ID, device, ground-truth height, output height and capture rejection.
   Rejected scans must also be counted when reporting usability/coverage.
4. Use subject-disjoint train, tuning, and held-out evaluation groups. Keep all
   scans of a person together. Do not tune to the held-out evaluation set.
5. Use `python evaluate_height.py validation.json` on accepted held-out scans.
   It reports signed bias, mean and 95th-percentile absolute error, worst error,
   and repeat-scan range. Evaluate device/body groups separately as well. Set
   tolerances with a tailor and validate against new subjects before production.
6. Height alone cannot validate circumferences or patterns. Measure each actual
   tailoring quantity independently, with matching definitions. Arm landmark
   length is not garment sleeve length; hip-to-ankle is not inseam. Training a
   garment model requires those separate labels and real fitting outcomes.

Example evaluation input (illustrative values, not a claimed validation result):

```json
[
  {"subject_id":"anonymous-001", "estimated_cm":172.3, "measured_cm":172.8,
   "ground_truth_method":"stadiometer"}
]
```

No new AI model has been trained in this update: no consented, independently
labelled dataset has been supplied. The existing pose model remains unchanged.

## Booth hardware and garment manufacturing

A booth should use calibrated camera/depth geometry and a fixed floor/head-height
reference rather than an entered guess. Add a calibrated scale if weight is needed.
Check sensors against known lengths/weights and log maintenance/recalibration.
Multiple viewpoints, occlusion checks and repeated scans can support surface
measurement, but still require validation. These are future hardware integrations,
not capabilities of this browser preview.

The proposed 20–30 minute suit service is not implemented or validated. Pattern
generation, fabric handling/cutting, sewing, pressing and fit checking need their
own manufacturing development and cycle-time trials. Scan completion alone must
never authorize automated garment production.

# Suit measurement prototype

A desktop webcam research prototype, not yet a phone app or validated tailoring scanner.

## Run

Use Python 3.10–3.12 in a virtual environment:

```powershell
python -m pip install -r requirements.txt
python main.py
```

Enter your measured height in inches. Face a level camera with the whole body visible,
arms slightly away from your sides. Press F when tracking passes visibility checks.
On the frozen image, click the top of the head and then the floor at the feet.
Press Enter to accept, R to reset marks, or Escape to cancel. If calibration is
rejected, run again and recapture. Keep the camera perpendicular to the body and
avoid wide-angle distortion. These steps reduce errors but do not establish accuracy.

Timestamped JSON reports are saved locally in `reports/`; images are not saved.
Reports contain body measurements, so protect or delete them as appropriate.

## What changed

The previous prototype used nose-to-heel distance as full height and inferred
circumferences from joint spacing and fixed ratios. Those outputs and automatic
clothing-size recommendations have been removed. This version uses manually marked
full height, preserves image aspect ratio, rejects low-visibility/clipped landmarks,
and reports only explicitly named projected landmark lengths. Arm lengths follow
shoulder-elbow-wrist rather than a straight shoulder-wrist chord.

Shoulder joint spacing is not tailoring shoulder width. Hip-to-ankle length is not
inseam. Chest, waist, hip, thigh, inseam, outseam, and garment sleeve measurements
require manual measurement. No garment patterns or cutting dimensions are produced.
Capture checks do not validate posture, perspective, or measurement accuracy.

## Verification and next milestone

```powershell
python -m unittest -v
```

Tests exercise invalid heights, capture rejection, calibration geometry, scale
invariance, and report metadata. Camera operation requires an interactive manual
test. Next, compare scans with repeated tailor measurements and define acceptable
error before adding silhouette-based circumferences or garment pattern generation.

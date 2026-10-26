# Suit measurement prototype

A local web application with a desktop webcam prototype. Not a validated tailoring scanner.

## Web version (start here)

Double-click `start-web.bat`, then open http://127.0.0.1:8765 in Chrome or Edge.
Alternatively run `.venv\Scripts\python.exe server.py` from this folder.
Keep the terminal open while testing. Stop the server with Ctrl+C.

1. Choose a garment and fit preference; enter measured height in feet/inches,
   centimetres, or total inches. Enter zero explicitly for zero inches.
2. Start the camera and allow browser access. Capture uses a five-second timer.
   Alternatively choose a JPEG, PNG, or WebP full-body photo.
3. After detection, mark the top of the head and floor at the feet on the frozen
   image. Sliders provide an alternative to clicking. Generate estimates.
4. Review camera estimates, optionally enter tape measurements, and download JSON.
   Display can switch between inches and centimetres; exports always use inches.
5. Clear the session to remove the image and measurements from the page.

The web app sends images only to the Python server on this computer. It does not
save photos, measurements, or profiles on the server. Downloaded reports remain on
your computer. There are no accounts, cloud synchronization, or production patterns.
The layout adapts to smaller screens, but the server binds only to localhost;
access from a separate phone is not configured. Android/iOS apps are future work.
Browser camera access requires localhost or HTTPS. If the in-app browser cannot
use your webcam, open the same address in Chrome/Edge or choose a photo.

Python dependencies must be installed before launching. MediaPipe's first model
initialization can take several seconds. Errors are shown above capture controls.

## Desktop version

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

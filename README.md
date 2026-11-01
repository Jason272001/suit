# Suit measurement prototype

A web application with browser-based body detection and a lightweight Python
measurement backend. Includes an optional desktop webcam prototype. Not a
validated tailoring scanner.

## Deploy to Vercel

Import `Jason272001/suit` with the repository root as the Root Directory. The
tracked `vercel.json` selects the Other framework preset, an empty build command,
`web` as the static output directory, and Python 3.12 functions in `api/`.
No environment variables, paid add-ons, or external image-processing service are
required. A push to the connected production branch starts a new deployment.

The root requirements file intentionally has no third-party dependencies. Do not
add the desktop camera packages to it: their combined dependencies exceeded
Vercel's 500 MB Python function bundle limit. Desktop dependencies are isolated
in `desktop/requirements.txt` and excluded from deployment. Model/WASM files in
`web/vendor/` are static downloads, excluded from the Python function bundle.

Open the successful deployment's HTTPS URL on your phone to test the camera.
Allow camera access when prompted. The first detection downloads roughly 16 MB
of self-hosted model/runtime assets (SIMD or non-SIMD variant); allow it to finish.
If a device cannot run the model, an error appears and you can retry with a
smaller image or a current browser. Physical Android/iOS testing is still needed.

## Web version (start here)

Double-click `start-web.bat`, then open http://127.0.0.1:8765 in Chrome or Edge.
Alternatively run `python server.py` from this folder (Python 3.10–3.12).
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

Photo pixels stay in the browser. Only 33 landmark coordinates, image dimensions,
entered height, and calibration marks are sent to `/api/measure`. The backend does
not save them. Downloaded reports remain on your device. There are no accounts,
cloud synchronization, or production patterns. The local server binds to localhost;
use the deployed HTTPS website to access the app from a separate phone.
Native Android/iOS apps are future work.
Browser camera access requires localhost or HTTPS. If the in-app browser cannot
use your webcam, open the same address in Chrome/Edge or choose a photo.

The web server needs no third-party Python packages. Body detection runs with the
pinned, self-hosted MediaPipe Tasks Vision 0.10.21 and Pose Landmarker Lite model.
First initialization can take several seconds. Errors appear above capture controls.

## Desktop version

Use Python 3.10–3.12 in a virtual environment:

```powershell
python -m pip install -r desktop/requirements.txt
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
python -S -m unittest -v
node --test test_detector.mjs
```

Tests exercise invalid heights, capture rejection, calibration geometry, scale
invariance, and report metadata. Camera operation requires an interactive manual
test. Next, compare scans with repeated tailor measurements and define acceptable
error before adding silhouette-based circumferences or garment pattern generation.

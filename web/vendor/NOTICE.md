# Browser pose detection assets

MediaPipe Tasks Vision **0.10.21**, Apache License 2.0 (see LICENSE).
Upstream: https://github.com/google-ai-edge/mediapipe
Distribution: https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.21/

Included files: vision_bundle.mjs, and the SIMD / non-SIMD WASM loaders and binaries
under wasm/. The original README is retained as MEDIAPIPE-README.md.

Pose Landmarker Lite float16 model, version 1:
https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task

All assets are served from this application's own origin. Inference runs in the
browser; image pixels are never submitted to the measurement API.

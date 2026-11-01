// Pinned, self-hosted MediaPipe runtime. Photo pixels stay in this browser.
let detectorPromise;
async function getDetector() {
  if (!detectorPromise) {
    detectorPromise = (async () => {
      const {FilesetResolver, PoseLandmarker} = await import('/vendor/vision_bundle.mjs');
      const files = await FilesetResolver.forVisionTasks('/vendor/wasm');
      return PoseLandmarker.createFromOptions(files, {
        baseOptions: {modelAssetPath:'/vendor/pose_landmarker_lite.task', delegate:'CPU'},
        runningMode:'IMAGE', numPoses:2, minPoseDetectionConfidence:0.7,
        minPosePresenceConfidence:0.7, outputSegmentationMasks:false
      });
    })().catch(error => { detectorPromise = null; throw error; });
  }
  return detectorPromise;
}

const required = [0,11,12,13,14,15,16,23,24,25,26,27,28,29,30];
export function captureIssue(points) {
  if (!points || points.length !== 33) return 'Full body not detected';
  for (const index of required) {
    const point = points[index];
    if (![point.x,point.y,point.visibility].every(Number.isFinite)) return 'Invalid landmark data';
    if (point.visibility < 0.7) return 'Keep your face, arms and both feet visible';
    if (point.x <= 0.02 || point.x >= 0.98 || point.y <= 0.02 || point.y >= 0.98) return 'Step back: keep your full body inside the frame';
  }
  return null;
}

export async function detectPhoto(image) {
  let detector;
  try { detector = await getDetector(); }
  catch { throw Error('Could not load body detection. Check your connection and retry. A current Chrome, Edge or Safari browser is required.'); }
  // Let the loading message paint before synchronous single-image inference.
  await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  let result;
  try { result = detector.detect(image); }
  catch { throw Error('Body detection could not run on this device. Try a smaller photo or a current browser.'); }
  if (result.landmarks.length > 1) throw Error('More than one person detected. Use a photo with only you in the frame.');
  const points = result.landmarks[0]?.map(p => ({x:p.x,y:p.y,visibility:p.visibility}));
  const issue = captureIssue(points);
  if (issue) throw Error(issue + '. Retake facing the camera with your head, hands and feet visible.');
  return {points,width:image.naturalWidth,height:image.naturalHeight};
}

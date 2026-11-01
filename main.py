"""Camera-assisted landmark estimates; not a validated tailoring scanner."""
import json
import math
from datetime import datetime, timezone
from pathlib import Path

cv2 = None
mp = None
REQUIRED = (0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 29, 30)
MANUAL = ('chest_circumference', 'waist_circumference', 'hip_circumference',
          'thigh_circumference', 'inseam', 'outseam', 'garment_sleeve_length')


def parse_height(raw):
    height = float(raw)
    if not math.isfinite(height) or not 24 <= height <= 100:
        raise ValueError('Enter a real height between 24 and 100 inches.')
    return height


def capture_issue(points):
    if not points or len(points) < 33:
        return 'Full body not detected'
    for i in REQUIRED:
        p = points[i]
        if not all(math.isfinite(v) for v in (p.x, p.y, p.visibility)):
            return 'Invalid landmark data'
        if p.visibility < 0.7:
            return 'Keep face, arms and both feet visible'
        if not 0.02 < p.x < 0.98 or not 0.02 < p.y < 0.98:
            return 'Step back: keep full body inside frame'
    return None


def estimate_measurements(points, width, height, height_inches, crown, floor):
    parse_height(str(height_inches))
    issue = capture_issue(points)
    if issue:
        raise ValueError(issue)
    if not all(math.isfinite(v) and v > 0 for v in (width, height)):
        raise ValueError('Invalid image dimensions')
    if not all(math.isfinite(v) for v in (crown, floor)):
        raise ValueError('Invalid calibration')
    if not 0 <= crown < floor < height or floor - crown < height * 0.4:
        raise ValueError('Mark head top, then floor at feet. Capture again to retry.')
    if crown >= points[0].y * height or floor < max(points[i].y * height for i in (29, 30)):
        raise ValueError('Height marks must enclose head and both heels.')
    scale = height_inches / (floor - crown)
    def length(a, b):
        return math.hypot((points[a].x - points[b].x) * width,
                          (points[a].y - points[b].y) * height) * scale
    return {
        'shoulder_landmark_span': length(11, 12),
        'left_arm_landmark_length': length(11, 13) + length(13, 15),
        'right_arm_landmark_length': length(12, 14) + length(14, 16),
        'left_hip_to_ankle_landmark_length': length(23, 25) + length(25, 27),
        'right_hip_to_ankle_landmark_length': length(24, 26) + length(26, 28),
    }


def capture(cap, pose):
    window = 'Suit Measurement Capture'
    while True:
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError('Camera stopped delivering frames.')
        # Preserve native aspect ratio; stretching distorts measurements.
        result = pose.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        points = result.pose_landmarks.landmark if result.pose_landmarks else None
        issue = capture_issue(points)
        view = frame.copy()
        if result.pose_landmarks:
            mp.solutions.drawing_utils.draw_landmarks(view, result.pose_landmarks, mp.solutions.pose.POSE_CONNECTIONS)
        cv2.putText(view, issue or 'Face camera, stand straight. F: capture; ESC: quit',
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (30, 220, 220), 2)
        cv2.imshow(window, view)
        key = cv2.waitKey(10) & 0xFF
        if key == 27 or cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
            return None
        if key == ord('f') and not issue:
            break
    marks = []
    def mark(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN and len(marks) < 2:
            marks.append(y)
    cv2.setMouseCallback(window, mark)
    try:
        while True:
            view = frame.copy()
            for y in marks:
                cv2.line(view, (0, y), (view.shape[1] - 1, y), (0, 220, 0), 2)
            cv2.putText(view, 'Click head TOP, then floor. Enter: accept; R: reset; ESC: quit',
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (30, 220, 220), 1)
            cv2.imshow(window, view)
            key = cv2.waitKey(10) & 0xFF
            if key == 27 or cv2.getWindowProperty(window, cv2.WND_PROP_VISIBLE) < 1:
                return None
            if key == ord('r'):
                marks.clear()
            if key == 13 and len(marks) == 2:
                return points, frame.shape[1], frame.shape[0], marks[0], marks[1]
    finally:
        cv2.setMouseCallback(window, lambda *args: None)


def save_report(values, height_inches, output_dir=None):
    folder = Path(output_dir) if output_dir else Path(__file__).parent / 'reports'
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc)
    path = folder / (stamp.strftime('measurements-%Y%m%dT%H%M%S-%fZ') + '.json')
    report = {
        'schema_version': 1, 'created_at': stamp.isoformat(), 'units': 'inches',
        'status': 'unvalidated_landmark_estimates', 'entered_height': height_inches,
        'calibration': 'user_marked_crown_and_floor', 'estimates': values,
        'requires_manual_measurement': list(MANUAL),
        'notes': ['Perspective, posture, clothing and landmark error affect results.',
                  'Landmark lengths are not garment dimensions or cutting patterns.',
                  'Confirm with a tailor before ordering or making clothes.'],
    }
    with path.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, allow_nan=False)
    return path


def main():
    global cv2, mp
    try:
        import cv2 as camera_module
        import mediapipe as pose_module
        cv2, mp = camera_module, pose_module
    except ImportError as exc:
        print(f'Missing dependency: {exc}. Install desktop/requirements.txt first.')
        return 1
    if not hasattr(mp, 'solutions'):
        print('This prototype requires the MediaPipe solutions API; see desktop/requirements.txt.')
        return 1
    while True:
        try:
            height_inches = parse_height(input('Enter measured height in inches (no default): ').strip())
            break
        except ValueError as exc:
            print(f'Invalid height: {exc}')
        except EOFError:
            print('No height supplied. Cancelled.')
            return 1
    cap = None
    pose = None
    try:
        pose = mp.solutions.pose.Pose(model_complexity=1, min_detection_confidence=0.7,
                                      min_tracking_confidence=0.7)
        for index in (0, 1, 2):
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                break
            cap.release()
        else:
            raise RuntimeError('Could not open camera 0, 1 or 2.')
        print('Use a level camera, full body visible, arms slightly away from sides.')
        data = capture(cap, pose)
        if data is None:
            print('Capture cancelled.')
            return 1
        points, width, height, crown, floor = data
        values = estimate_measurements(points, width, height, height_inches, crown, floor)
        path = save_report(values, height_inches)
        print('\nUnvalidated landmark estimates (inches):')
        for name, value in values.items():
            print(f'  {name}: {value:.1f}')
        print(f'Manual tailoring measurements still required. Report saved to {path}')
        return 0
    except (RuntimeError, ValueError, OSError, cv2.error) as exc:
        print(f'Measurement failed: {exc}')
        return 1
    finally:
        if cap is not None:
            cap.release()
        if pose is not None:
            pose.close()
        cv2.destroyAllWindows()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print('\nCancelled.')
        raise SystemExit(130)

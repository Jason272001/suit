"""Reference-based scale estimation. Geometry checks are not accuracy certification."""
import math

from main import capture_issue, parse_height


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{label} must be a finite number.')
    return value


def upright_issue(points, width, height):
    issue = capture_issue(points)
    if issue:
        return issue
    def midpoint(a, b):
        return ((points[a].x + points[b].x) * width / 2,
                (points[a].y + points[b].y) * height / 2)
    shoulders, hips = midpoint(11, 12), midpoint(23, 24)
    knees, ankles = midpoint(25, 26), midpoint(27, 28)
    if not shoulders[1] < hips[1] < knees[1] < ankles[1]:
        return 'Stand upright with straight legs and keep the camera level.'
    torso_height = hips[1] - shoulders[1]
    if abs(hips[0] - shoulders[0]) > torso_height * math.tan(math.radians(12)):
        return 'Your torso is leaning. Stand straight and retake the scan.'
    body_span = ankles[1] - points[0].y * height
    if abs(points[11].x - points[12].x) * width < body_span * 0.12:
        return 'Face the camera directly; a side view cannot calibrate this scan.'
    return None


def resolve_height(data, points):
    width = number(data['width'], 'Image width')
    height = number(data['height'], 'Image height')
    crown = number(data['crown'], 'Top of head')
    floor = number(data['floor'], 'Floor')
    if width <= 0 or height <= 0:
        raise ValueError('Image dimensions must be positive.')
    if not 0 <= crown < floor < height or floor - crown < height * 0.4:
        raise ValueError('Mark your full height from head top to floor, filling at least 40% of the image.')
    if crown >= points[0].y * height or floor < max(points[i].y * height for i in (29, 30)):
        raise ValueError('Height marks must enclose the head and both heels.')
    mode = data.get('height_source', 'entered')
    if mode not in ('entered', 'reference'):
        raise ValueError('Choose a supported height source.')
    entered = data.get('height_inches')
    if entered is not None:
        entered = parse_height(str(number(entered, 'Entered height')))
    if mode == 'entered':
        if entered is None:
            raise ValueError('Enter a measured height or choose reference-object calibration.')
        return {'source': mode, 'inches': entered, 'entered_inches': entered,
                'verified': False, 'status': 'entered_height_unverified',
                'comparison': None, 'reference': None}
    issue = upright_issue(points, width, height)
    if issue:
        raise ValueError(issue)
    reference = data.get('reference')
    if not isinstance(reference, dict) or reference.get('setup_confirmed') is not True:
        raise ValueError('Confirm the reference is flat, vertical, and beside you at the same distance from the camera.')
    length = number(reference['length_cm'], 'Reference length')
    if not 10 <= length <= 200:
        raise ValueError('Use a reference length between 10 and 200 cm.')
    ends = []
    for label in ('top', 'bottom'):
        point = reference[label]
        x, y = number(point['x'], 'Reference X'), number(point['y'], 'Reference Y')
        if not 0 <= x < width or not 0 <= y < height:
            raise ValueError('Keep both reference marks inside the image.')
        ends.append((x, y))
    (x1, y1), (x2, y2) = ends
    span = y2 - y1
    if span < max(40, height * 0.10):
        raise ValueError('Reference is too small or reversed. Mark its top then bottom; it must span at least 10% of image height and 40 pixels.')
    if abs(x2 - x1) > span * math.tan(math.radians(5)):
        raise ValueError('Reference is tilted. Hold its measured edge vertically and retake the photo.')
    if y1 < crown or y2 > floor:
        raise ValueError('Place the reference between your head and the floor, beside your body.')
    estimated = parse_height(str((floor - crown) * length / span / 2.54))
    comparison = None
    status = 'reference_height_unvalidated'
    if entered is not None:
        difference = estimated - entered
        comparison = {'difference_inches': difference, 'threshold_inches': 1.0,
                      'conflict': abs(difference) >= 1.0 - 1e-9}
        if comparison['conflict']:
            status = 'height_conflict'
    return {'source': mode, 'inches': estimated, 'entered_inches': entered,
            'verified': False, 'status': status, 'comparison': comparison,
            'reference': {'length_cm': length, 'pixel_span': span,
                          'top': reference['top'], 'bottom': reference['bottom'],
                          'setup_confirmed_by_user': True}}

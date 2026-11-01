import test from 'node:test';
import assert from 'node:assert/strict';
import {captureIssue} from './web/detector.js';

test('missing body, clipped points, hidden points and invalid data are rejected', () => {
  assert.ok(captureIssue(undefined));
  assert.ok(captureIssue([]));
  const points = Array.from({length:33},()=>({x:0.5,y:0.5,visibility:0.99}));
  assert.equal(captureIssue(points),null);
  for (const [key,value] of [['x',0.99],['y',NaN],['visibility',0.2]]) {
    const old = points[11][key];
    points[11][key] = value;
    assert.ok(captureIssue(points));
    points[11][key] = old;
  }
});

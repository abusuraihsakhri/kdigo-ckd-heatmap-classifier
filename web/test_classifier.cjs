'use strict';
const assert = require('node:assert/strict');
const test = require('node:test');
const { classify, G, A, grid } = require('./classifier.js');

test('full KDIGO 2024 18-cell risk matrix', () => {
  const egfr = [100, 75, 52, 38, 22, 10];
  const acr = [10, 100, 500];
  egfr.forEach((e, i) => acr.forEach((a, j) => {
    const result = classify(e, a);
    assert.equal(result.stage, G[i] + A[j]);
    assert.equal(result.risk_category, grid[i][j]);
  }));
});

test('exact boundaries', () => {
  [[90, 'G1'], [60, 'G2'], [45, 'G3a'], [30, 'G3b'], [15, 'G4'], [14.99, 'G5']]
    .forEach(([e, expected]) => assert.equal(classify(e, 30).gfr_category, expected));
  [[29.99, 'A1'], [30, 'A2'], [300, 'A3'], [299.99, 'A2'], [300.01, 'A3']]
    .forEach(([a, expected]) => assert.equal(classify(90, a).albuminuria_category, expected));
});

test('rejects blank, invalid and nonfinite input', () => {
  ['', ' ', -1, 'nope', NaN, Infinity, null, undefined].forEach(value => {
    assert.throws(() => classify(value, 30));
    assert.throws(() => classify(45, value));
  });
});

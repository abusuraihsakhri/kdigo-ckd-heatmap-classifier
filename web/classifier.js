/* KDIGO 2024 CKD GFR–albuminuria classification, no network calls. */
(function (root) {
  'use strict';
  const G = ['G1', 'G2', 'G3a', 'G3b', 'G4', 'G5'];
  const A = ['A1', 'A2', 'A3'];
  const grid = [
    ['low', 'moderately increased', 'high'],
    ['low', 'moderately increased', 'high'],
    ['moderately increased', 'high', 'very high'],
    ['high', 'very high', 'very high'],
    ['very high', 'very high', 'very high'],
    ['very high', 'very high', 'very high']
  ];
  const chronicityNote = 'A single result cannot diagnose CKD. Kidney abnormalities must be present for at least three months or other evidence of chronic kidney disease must be established.';
  function numeric(value, label) {
    if (value === null || value === undefined || String(value).trim() === '') {
      throw new Error(label + ' is required');
    }
    const number = Number(value);
    if (!Number.isFinite(number) || number < 0) {
      throw new Error(label + ' must be a finite, nonnegative number');
    }
    return number;
  }
  function classify(egfr, acr_mg_g) {
    egfr = numeric(egfr, 'eGFR');
    acr_mg_g = numeric(acr_mg_g, 'ACR');
    const g = egfr >= 90 ? 0 : egfr >= 60 ? 1 : egfr >= 45 ? 2 :
      egfr >= 30 ? 3 : egfr >= 15 ? 4 : 5;
    const a = acr_mg_g < 30 ? 0 : acr_mg_g <= 300 ? 1 : 2;
    return {
      egfr, acr_mg_g, gfr_category: G[g], albuminuria_category: A[a],
      stage: G[g] + A[a], risk_category: grid[g][a],
      clinical_note: chronicityNote + (g <= 1 && a === 0 ?
        ' Without other markers of kidney damage, G1A1 and G2A1 do not meet CKD criteria.' : '')
    };
  }
  const api = Object.freeze({ classify, grid, G, A });
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  if (root) root.KDIGO = api;
})(typeof window !== 'undefined' ? window : undefined);

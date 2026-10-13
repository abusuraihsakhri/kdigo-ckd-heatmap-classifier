/* UI only: all clinical calculations are in classifier.js. */
(function () {
  'use strict';
  const model = window.KDIGO;
  const form = document.getElementById('classify-form');
  const result = document.getElementById('result');
  const matrix = document.getElementById('heatmap-body');
  const upload = document.getElementById('csv-upload');
  const download = document.getElementById('download');
  const batchStatus = document.getElementById('batch-summary');
  const gfrRanges = ['≥90', '60–<90', '45–<60', '30–<45', '15–<30', '<15'];
  let exportedCSV = '';

  function fillResult(text, className) {
    result.replaceChildren();
    const paragraph = document.createElement('p');
    paragraph.textContent = text;
    if (className) paragraph.className = className;
    result.append(paragraph);
  }

  function buildHeatmap() {
    model.G.forEach((g, row) => {
      const tr = document.createElement('tr');
      const th = document.createElement('th');
      th.scope = 'row';
      th.className = 'rowhead';
      th.textContent = g + ' · ' + gfrRanges[row];
      tr.append(th);
      model.A.forEach((a, column) => {
        const td = document.createElement('td');
        const risk = model.grid[row][column];
        td.className = risk.replaceAll(' ', '-');
        td.dataset.stage = g + a;
        td.textContent = risk;
        tr.append(td);
      });
      matrix.append(tr);
    });
  }

  function classify(event) {
    event.preventDefault();
    try {
      const output = model.classify(
        document.getElementById('egfr').value,
        document.getElementById('acr').value
      );
      const heading = document.createElement('div');
      heading.className = 'risk-name';
      heading.textContent = output.stage + ' — ' + output.risk_category + ' risk';
      const details = document.createElement('p');
      details.textContent = 'GFR category ' + output.gfr_category + '; albuminuria ' +
        output.albuminuria_category + '.';
      const note = document.createElement('p');
      note.className = 'muted';
      note.textContent = output.clinical_note;
      result.replaceChildren(heading, details, note);
      matrix.querySelectorAll('td').forEach(cell => {
        cell.classList.toggle('active', cell.dataset.stage === output.stage);
        if (cell.dataset.stage === output.stage) cell.setAttribute('aria-current', 'true');
        else cell.removeAttribute('aria-current');
      });
    } catch (error) {
      fillResult(error.message, 'error');
      matrix.querySelectorAll('.active').forEach(cell => {
        cell.classList.remove('active');
        cell.removeAttribute('aria-current');
      });
    }
  }

  function parseCSV(text) {
    const rows = [];
    let row = [], field = '', quoted = false, afterQuote = false;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (quoted) {
        if (c === '"') {
          if (text[i + 1] === '"') { field += '"'; i++; }
          else { quoted = false; afterQuote = true; }
        } else field += c;
      } else if (afterQuote) {
        if (c === ',') { row.push(field); field = ''; afterQuote = false; }
        else if (c === '\n' || c === '\r') {
          row.push(field); rows.push(row); row = []; field = ''; afterQuote = false;
          if (c === '\r' && text[i + 1] === '\n') i++;
        } else throw new Error('Malformed CSV: characters following closing quotation mark');
      } else if (c === '"' && field === '') {
        quoted = true;
      } else if (c === '"') {
        throw new Error('Malformed CSV: unexpected quotation mark');
      } else if (c === ',') {
        row.push(field); field = '';
      } else if (c === '\n' || c === '\r') {
        row.push(field); rows.push(row); row = []; field = '';
        if (c === '\r' && text[i + 1] === '\n') i++;
      } else field += c;
    }
    if (quoted) throw new Error('Malformed CSV: unterminated quoted field');
    if (field !== '' || row.length || afterQuote) { row.push(field); rows.push(row); }
    return rows;
  }

  function escapeCSV(value) {
    let item = String(value == null ? '' : value);
    if (/^\s*[=+@\-\t\r]/.test(item)) item = "'" + item;
    return '"' + item.replaceAll('"', '""') + '"';
  }

  async function processUpload() {
    exportedCSV = '';
    download.disabled = true;
    const file = upload.files && upload.files[0];
    if (!file) { batchStatus.textContent = ''; return; }
    if (file.size > 5 * 1024 * 1024) {
      batchStatus.textContent = 'Error: CSV exceeds the 5 MiB limit.';
      return;
    }
    batchStatus.textContent = 'Reading CSV…';
    try {
      const rows = parseCSV((await file.text()).replace(/^\uFEFF/, ''));
      const header = rows.shift();
      if (!header || !header.includes('egfr') || !header.includes('acr_mg_g') ||
          new Set(header).size !== header.length || header.some(h => !h)) {
        throw new Error("CSV needs unique column names including 'egfr' and 'acr_mg_g'.");
      }
      const g = header.indexOf('egfr');
      const a = header.indexOf('acr_mg_g');
      if (rows.length > 10000) throw new Error('CSV exceeds 10,000 records.');
      const outputColumns = header.filter(h => !['stage', 'risk_category', 'error'].includes(h))
        .concat(['stage', 'risk_category', 'error']);
      const output = [outputColumns];
      let success = 0, invalid = 0;
      rows.forEach((row) => {
        if (row.length === 1 && row[0] === '') return;
        let stage = '', risk = '', error = '';
        if (row.length !== header.length) {
          error = 'CSV column count does not match header';
        } else {
          try {
            const classification = model.classify(row[g], row[a]);
            stage = classification.stage;
            risk = classification.risk_category;
          } catch (ex) { error = ex.message; }
        }
        if (error) invalid++; else success++;
        const record = {};
        header.forEach((column, index) => { record[column] = row[index] || ''; });
        record.stage = stage;
        record.risk_category = risk;
        record.error = error;
        output.push(outputColumns.map(column => record[column] || ''));
      });
      exportedCSV = output.map(row => row.map(escapeCSV).join(',')).join('\r\n') + '\r\n';
      download.disabled = false;
      batchStatus.textContent = success + ' classified; ' + invalid +
        ' invalid rows retained with explanations. No file uploaded.';
    } catch (error) {
      batchStatus.textContent = 'Error: ' + error.message;
    }
  }

  function saveCSV() {
    if (!exportedCSV) return;
    const blob = new Blob([exportedCSV], { type:'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'kdigo_classified.csv';
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  buildHeatmap();
  form.addEventListener('submit', classify);
  document.getElementById('clear').addEventListener('click', () => {
    form.reset();
    document.getElementById('egfr').value = '';
    document.getElementById('acr').value = '';
    fillResult('Enter values to classify.', 'muted');
    matrix.querySelectorAll('.active').forEach(cell => {
      cell.classList.remove('active');
      cell.removeAttribute('aria-current');
    });
  });
  upload.addEventListener('change', processUpload);
  download.addEventListener('click', saveCSV);
})();
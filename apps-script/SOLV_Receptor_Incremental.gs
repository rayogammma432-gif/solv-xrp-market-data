// Receptor incremental 1m/15m/1H/4H para SOLVUSDT
// + puente SIGNALS/PERFORMANCE para forward tracking.
// El secreto NO se guarda en el código.
// Apps Script > Project Settings > Script properties:
// SHARED_SECRET = el mismo secreto que ya usa config.json en el Motorola.

const SPREADSHEET_ID = '1H6oLPDHQKX3zpKVvWS_FhE3lUNnNtE0uEwLSIFZYPY8';
const ASSET_SYMBOL = 'SOLVUSDT';
const ASSET_PREFIX = 'SOLV';
const SIGNAL_COLS = 23; // A:W

const MAX_ROWS = {
  '1M': 500,
  '15M': 500,
  '1H': 500,
  '4H': 500,
  'OI_1M': 1440,
  'OI_HISTORY': 96
};

function jsonOut_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function sheet_(ss, name) {
  const sh = ss.getSheetByName(name);
  if (!sh) throw new Error('Falta la pestaña: ' + name);
  return sh;
}

function ensureRows_(sh, neededLastRow) {
  if (sh.getMaxRows() < neededLastRow) {
    sh.insertRowsAfter(sh.getMaxRows(), neededLastRow - sh.getMaxRows());
  }
}

function fullReplace_(sh, rows, cols, maxDataRows) {
  rows = Array.isArray(rows) ? rows.slice(-maxDataRows) : [];
  ensureRows_(sh, Math.max(2, rows.length + 1));
  const clearRows = Math.max(1, sh.getMaxRows() - 1);
  sh.getRange(2, 1, clearRows, cols).clearContent();
  if (rows.length) {
    sh.getRange(2, 1, rows.length, cols).setValues(rows);
  }
  return rows.length;
}

function appendNew_(sh, rows, cols, maxDataRows) {
  if (!Array.isArray(rows) || !rows.length) return 0;

  rows = rows.slice().sort(function(a, b) {
    return String(a[0]).localeCompare(String(b[0]));
  });

  let lastRow = sh.getLastRow();
  let lastTs = lastRow >= 2 ? String(sh.getRange(lastRow, 1).getValue()) : '';
  const toAppend = [];

  rows.forEach(function(row) {
    const ts = String(row[0]);
    if (!lastTs || ts > lastTs) {
      toAppend.push(row);
      lastTs = ts;
    }
  });

  if (!toAppend.length) return 0;

  const startRow = sh.getLastRow() + 1;
  ensureRows_(sh, startRow + toAppend.length - 1);
  sh.getRange(startRow, 1, toAppend.length, cols).setValues(toAppend);

  const dataRows = sh.getLastRow() - 1;
  if (dataRows > maxDataRows) {
    const excess = dataRows - maxDataRows;
    sh.deleteRows(2, excess);
    sh.insertRowsAfter(sh.getMaxRows(), excess);
  }
  return toAppend.length;
}

function maxForSheet_(name) {
  if (name === 'OI_1M') return MAX_ROWS.OI_1M;
  if (name === 'OI_HISTORY') return MAX_ROWS.OI_HISTORY;
  if (/_1M$/.test(name)) return MAX_ROWS['1M'];
  if (/_15M$/.test(name)) return MAX_ROWS['15M'];
  if (/_1H$/.test(name)) return MAX_ROWS['1H'];
  if (/_4H$/.test(name)) return MAX_ROWS['4H'];
  return 500;
}

function updateMarket_(ss, market, generatedAtUtc, status) {
  const sh = sheet_(ss, 'MARKET');
  const values = [
    [ASSET_SYMBOL],
    [Number(market.markPrice)],
    [Number(market.indexPrice)],
    [Number(market.fundingRate)],
    [String(market.nextFundingTimeUtc || '')],
    [Number(market.openInterest)],
    [String(generatedAtUtc || new Date().toISOString())],
    [status || 'OK']
  ];
  sh.getRange(2, 2, 8, 1).setValues(values);
}

function replaceLiveState_(ss, rows) {
  const sh = sheet_(ss, 'LIVE_STATE');
  const cols = 5;
  const clearRows = Math.max(1, sh.getMaxRows() - 1);
  sh.getRange(2, 1, clearRows, cols).clearContent();
  if (Array.isArray(rows) && rows.length) {
    ensureRows_(sh, rows.length + 1);
    sh.getRange(2, 1, rows.length, cols).setValues(rows);
  }
}

function getOpenSignals_(ss) {
  const sh = sheet_(ss, 'SIGNALS');
  const lastRow = sh.getLastRow();
  if (lastRow < 2) return [];

  const rows = sh.getRange(2, 1, lastRow - 1, SIGNAL_COLS).getValues();
  const out = [];

  rows.forEach(function(r, i) {
    if (String(r[11] || '').toUpperCase() !== 'OPEN') return;
    if (!String(r[0] || '')) return;

    out.push({
      row: i + 2,
      id: String(r[0] || ''),
      signalUtc: String(r[1] || ''),
      motor: String(r[2] || ''),
      direction: String(r[3] || ''),
      setup: String(r[4] || ''),
      entry: r[5] === '' ? null : Number(r[5]),
      stop: r[6] === '' ? null : Number(r[6]),
      tp1: r[7] === '' ? null : Number(r[7]),
      tp2: r[8] === '' ? null : Number(r[8]),
      riskPct: r[9] === '' ? null : Number(r[9]),
      confluences: String(r[10] || ''),
      state: String(r[11] || ''),
      result: String(r[12] || ''),
      resultR: r[13] === '' ? null : Number(r[13]),
      mfeR: r[14] === '' ? null : Number(r[14]),
      maeR: r[15] === '' ? null : Number(r[15]),
      barsElapsed: r[16] === '' ? 0 : Number(r[16]),
      tp1HitUtc: String(r[17] || ''),
      closeUtc: String(r[18] || ''),
      exitPrice: r[19] === '' ? null : Number(r[19]),
      exitReason: String(r[20] || ''),
      timeStopStatus: String(r[21] || ''),
      notes: String(r[22] || '')
    });
  });

  return out;
}

function applySignalUpdates_(ss, updates) {
  if (!Array.isArray(updates) || !updates.length) return 0;

  const sh = sheet_(ss, 'SIGNALS');
  const lastRow = sh.getLastRow();
  if (lastRow < 2) return 0;

  const ids = sh.getRange(2, 1, lastRow - 1, 1).getValues();
  const rowById = {};
  ids.forEach(function(r, i) {
    const id = String(r[0] || '');
    if (id) rowById[id] = i + 2;
  });

  let changed = 0;

  updates.forEach(function(u) {
    const id = String((u && u.id) || '');
    const row = rowById[id];
    if (!row) return;

    const range = sh.getRange(row, 12, 1, 12); // L:W
    const cur = range.getValues()[0];

    function put(idx, key, numeric) {
      if (!Object.prototype.hasOwnProperty.call(u, key)) return;
      const v = u[key];
      if (v === null || typeof v === 'undefined') {
        cur[idx] = '';
      } else if (numeric) {
        cur[idx] = Number(v);
      } else {
        cur[idx] = String(v);
      }
    }

    put(0, 'state', false);
    put(1, 'result', false);
    put(2, 'resultR', true);
    put(3, 'mfeR', true);
    put(4, 'maeR', true);
    put(5, 'barsElapsed', true);
    put(6, 'tp1HitUtc', false);
    put(7, 'closeUtc', false);
    put(8, 'exitPrice', true);
    put(9, 'exitReason', false);
    put(10, 'timeStopStatus', false);
    put(11, 'notes', false);

    range.setValues([cur]);
    changed++;
  });

  return changed;
}

function doPost(e) {
  try {
    const secretExpected = PropertiesService.getScriptProperties().getProperty('SHARED_SECRET');
    if (!secretExpected) {
      throw new Error('Falta Script Property SHARED_SECRET');
    }

    const body = e && e.postData && e.postData.contents ? e.postData.contents : '{}';
    const payload = JSON.parse(body);

    if (String(payload.secret || '') !== String(secretExpected)) {
      return jsonOut_({ok:false, error:'UNAUTHORIZED'});
    }

    const mode = String(payload.mode || 'bootstrap').toLowerCase();
    if (mode !== 'bootstrap' && mode !== 'incremental') {
      throw new Error('mode inválido: ' + mode);
    }

    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    const counts = {};
    const incomingSheets = payload.sheets || {};

    Object.keys(incomingSheets).forEach(function(name) {
      const rows = incomingSheets[name];
      const sh = sheet_(ss, name);
      const maxRows = maxForSheet_(name);
      if (mode === 'bootstrap') {
        counts[name] = fullReplace_(sh, rows, 11, maxRows);
      } else {
        counts[name] = appendNew_(sh, rows, 11, maxRows);
      }
    });

    if (Array.isArray(payload.oiHistory)) {
      counts.OI_HISTORY = fullReplace_(
        sheet_(ss, 'OI_HISTORY'),
        payload.oiHistory,
        6,
        MAX_ROWS.OI_HISTORY
      );
    }

    if (Array.isArray(payload.oi1m)) {
      const oi1mSheet = sheet_(ss, 'OI_1M');
      if (mode === 'bootstrap') {
        counts.OI_1M = fullReplace_(
          oi1mSheet,
          payload.oi1m,
          9,
          MAX_ROWS.OI_1M
        );
      } else {
        counts.OI_1M = appendNew_(
          oi1mSheet,
          payload.oi1m,
          9,
          MAX_ROWS.OI_1M
        );
      }
    }

    if (Array.isArray(payload.liveState)) {
      replaceLiveState_(ss, payload.liveState);
      counts.LIVE_STATE = payload.liveState.length;
    }

    if (Array.isArray(payload.signalUpdates)) {
      counts.SIGNAL_UPDATES = applySignalUpdates_(ss, payload.signalUpdates);
    }

    if (!payload.market) throw new Error('Falta market');
    updateMarket_(ss, payload.market, payload.generatedAtUtc, 'OK');

    SpreadsheetApp.flush();

    return jsonOut_({
      ok: true,
      status: 'OK',
      mode: mode,
      updatedAtUtc: payload.generatedAtUtc || new Date().toISOString(),
      rows: counts,
      openSignals: getOpenSignals_(ss)
    });

  } catch (err) {
    return jsonOut_({
      ok: false,
      error: String(err && err.message ? err.message : err)
    });
  }
}

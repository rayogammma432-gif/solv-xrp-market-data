// Receptor incremental 1m/15m/1H/4H para SOLVUSDT
// El secreto NO se guarda en el código.
// Apps Script > Project Settings > Script properties:
// SHARED_SECRET = el mismo secreto que ya usa config.json en el Motorola.

const SPREADSHEET_ID = '1H6oLPDHQKX3zpKVvWS_FhE3lUNnNtE0uEwLSIFZYPY8';
const ASSET_SYMBOL = 'SOLVUSDT';
const ASSET_PREFIX = 'SOLV';

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

    if (!payload.market) throw new Error('Falta market');
    updateMarket_(ss, payload.market, payload.generatedAtUtc, 'OK');

    SpreadsheetApp.flush();

    return jsonOut_({
      ok: true,
      status: 'OK',
      mode: mode,
      updatedAtUtc: payload.generatedAtUtc || new Date().toISOString(),
      rows: counts
    });

  } catch (err) {
    return jsonOut_({
      ok: false,
      error: String(err && err.message ? err.message : err)
    });
  }
}

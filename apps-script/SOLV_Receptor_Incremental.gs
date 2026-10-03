// Receptor incremental 1m/5m/15m/1H/4H/1D para SOLVUSDT
// + puente SIGNALS/PERFORMANCE para forward tracking.
// El secreto NO se guarda en el código.
// Apps Script > Project Settings > Script properties:
// SHARED_SECRET = el mismo secreto que ya usa config.json en el Motorola.

const SPREADSHEET_ID = '1H6oLPDHQKX3zpKVvWS_FhE3lUNnNtE0uEwLSIFZYPY8';
const ARCHIVE_SPREADSHEET_ID = '1_GlUrC_n1-q0juk0-28dQ6ZdIdGFTutbrglYhKlpIIk';
const ASSET_SYMBOL = 'SOLVUSDT';
const ASSET_PREFIX = 'SOLV';
const SOLV_V3_4_RECEPTOR_VERSION = 'SOLV_RECEPTOR_V3_4_V1';
const SOLV_V3_4_RULE_VERSION = 'SOLV_V3.4';
const SOLV_V3_4_SCHEMA_VERSION = 'SOLV_V3_4_SCHEMA_EC_AQ_V1';
const SIGNAL_COLS = 43; // A:AQ
const ANALYSIS_COLS = 133; // A:EC
const MAX_RESEARCH_ROWS = 3000;

const MAX_ROWS = {
  '1M': 500,
  '15M': 500,
  '1H': 500,
  '4H': 500,
  '1D': 500,
  'OI_1M': 1440,
  'OI_HISTORY': 96
};

function jsonOut_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function doGet(e) {
  return jsonOut_({
    ok: true,
    mode: 'HEALTH',
    receptorVersion: SOLV_V3_4_RECEPTOR_VERSION,
    ruleVersion: SOLV_V3_4_RULE_VERSION,
    schemaVersion: SOLV_V3_4_SCHEMA_VERSION,
    spreadsheetId: SPREADSHEET_ID,
    signalCols: SIGNAL_COLS,
    analysisCols: ANALYSIS_COLS
  });
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

function appendArchiveNew_(sh, rows, cols) {
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
      toAppend.push(row.slice(0, cols));
      lastTs = ts;
    }
  });

  if (!toAppend.length) return 0;

  const startRow = sh.getLastRow() + 1;
  ensureRows_(sh, startRow + toAppend.length - 1);
  sh.getRange(startRow, 1, toAppend.length, cols).setValues(toAppend);
  return toAppend.length;
}

function archiveResearch_(incomingSheets, oi1m) {
  const archive = SpreadsheetApp.openById(ARCHIVE_SPREADSHEET_ID);
  return {
    SOLV_1M: appendArchiveNew_(
      sheet_(archive, 'SOLV_1M_ARCHIVE'),
      incomingSheets['SOLV_1M'] || [],
      11
    ),
    BTC_1M: appendArchiveNew_(
      sheet_(archive, 'BTC_1M_ARCHIVE'),
      incomingSheets['BTC_1M'] || [],
      11
    ),
    OI_1M: appendArchiveNew_(
      sheet_(archive, 'OI_1M_ARCHIVE'),
      Array.isArray(oi1m) ? oi1m : [],
      9
    )
  };
}

function maxForSheet_(name) {
  if (name === 'OI_1M') return MAX_ROWS.OI_1M;
  if (name === 'OI_HISTORY') return MAX_ROWS.OI_HISTORY;
  if (/_1M$/.test(name)) return MAX_ROWS['1M'];
  if (/_15M$/.test(name)) return MAX_ROWS['15M'];
  if (/_1H$/.test(name)) return MAX_ROWS['1H'];
  if (/_4H$/.test(name)) return MAX_ROWS['4H'];
  if (/_1D$/.test(name)) return MAX_ROWS['1D'];
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
      notes: String(r[22] || ''),
      mfe5mR: r[23] === '' ? null : Number(r[23]),
      mae5mR: r[24] === '' ? null : Number(r[24]),
      rsi5m: r[25] === '' ? null : Number(r[25]),
      ema20Side5m: String(r[26] || ''),
      micro5m: String(r[27] || ''),
      mfe10mR: r[28] === '' ? null : Number(r[28]),
      mae10mR: r[29] === '' ? null : Number(r[29]),
      rsi10m: r[30] === '' ? null : Number(r[30]),
      ema20Side10m: String(r[31] || ''),
      micro10m: String(r[32] || ''),
      mfe15mR: r[33] === '' ? null : Number(r[33]),
      mae15mR: r[34] === '' ? null : Number(r[34]),
      rsi15m: r[35] === '' ? null : Number(r[35]),
      ema20Side15m: String(r[36] || ''),
      micro15m: String(r[37] || ''),
      thesisId: String(r[38] || ''),
      ruleVersion: String(r[39] || ''),
      liveMode: String(r[40] || ''),
      executionGate: String(r[41] || ''),
      thesisExpiresUtc: String(r[42] || '')
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

    const range = sh.getRange(row, 12, 1, 27); // L:AL
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

    // Telemetría pasiva 1m para SCALP. No modifica TIME STOP.
    put(12, 'mfe5mR', true);
    put(13, 'mae5mR', true);
    put(14, 'rsi5m', true);
    put(15, 'ema20Side5m', false);
    put(16, 'micro5m', false);

    put(17, 'mfe10mR', true);
    put(18, 'mae10mR', true);
    put(19, 'rsi10m', true);
    put(20, 'ema20Side10m', false);
    put(21, 'micro10m', false);

    put(22, 'mfe15mR', true);
    put(23, 'mae15mR', true);
    put(24, 'rsi15m', true);
    put(25, 'ema20Side15m', false);
    put(26, 'micro15m', false);

    range.setValues([cur]);
    changed++;
  });

  return changed;
}


function getPendingAnalyses_(ss) {
  const sh = sheet_(ss, 'ANALYSES');
  const lastRow = sh.getLastRow();
  if (lastRow < 2) return [];

  const rows = sh.getRange(2, 1, lastRow - 1, ANALYSIS_COLS).getValues();
  const out = [];

  rows.forEach(function(r, i) {
    const id = String(r[0] || '');
    if (!id) return;
    const status = String(r[42] || 'PENDING').toUpperCase();
    if (status === 'COMPLETE') return;

    out.push({
      row: i + 2,
      analysisId: id,
      analysisUtc: String(r[1] || ''),
      overallState: String(r[3] || ''),
      primaryBias: String(r[4] || ''),
      scalpBias: String(r[7] || ''),
      markPrice: r[17] === '' ? null : Number(r[17]),
      entry: r[19] === '' ? null : Number(r[19]),
      stop: r[20] === '' ? null : Number(r[20]),
      tp1: r[21] === '' ? null : Number(r[21]),
      tp2: r[22] === '' ? null : Number(r[22]),
      ruleVersion: String(r[57] || ''),
      liveMode: String(r[114] || ''),
      executionGate: String(r[115] || ''),
      planDirection: String(r[116] || ''),
      geometryValid: String(r[117] || ''),
      thesisId: String(r[118] || ''),
      thesisExpiresUtc: String(r[119] || ''),
      thesisLifecycle: String(r[120] || ''),
      shadowTp1OneR: r[130] === '' ? null : Number(r[130]),
      outcomeStatus: status || 'PENDING'
    });
  });

  return out.slice(-500);
}

function applyAnalysisUpdates_(ss, updates) {
  if (!Array.isArray(updates) || !updates.length) return 0;

  const sh = sheet_(ss, 'ANALYSES');
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
    const id = String((u && u.analysisId) || '');
    const row = rowById[id];
    if (!row) return;

    const range = sh.getRange(row, 32, 1, 13); // AF:AR
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

    put(0, 'fwd5mPct', true);
    put(1, 'fwd15mPct', true);
    put(2, 'fwd30mPct', true);
    put(3, 'fwd60mPct', true);
    put(4, 'fwd240mPct', true);
    put(5, 'mfe15mPct', true);
    put(6, 'mae15mPct', true);
    put(7, 'mfe60mPct', true);
    put(8, 'mae60mPct', true);
    put(9, 'mfe240mPct', true);
    put(10, 'mae240mPct', true);
    put(11, 'outcomeStatus', false);
    put(12, 'notes', false);
    range.setValues([cur]);

    if (
      Object.prototype.hasOwnProperty.call(u, 'planDirection') ||
      Object.prototype.hasOwnProperty.call(u, 'geometryValid')
    ) {
      const planRange = sh.getRange(row, 117, 1, 2); // DM:DN
      const planCur = planRange.getValues()[0];
      if (Object.prototype.hasOwnProperty.call(u, 'planDirection')) {
        planCur[0] = u.planDirection == null ? '' : String(u.planDirection);
      }
      if (Object.prototype.hasOwnProperty.call(u, 'geometryValid')) {
        planCur[1] = u.geometryValid == null ? '' : String(u.geometryValid);
      }
      planRange.setValues([planCur]);
    }

    const execKeys = [
      'entryFilledUtc', 'firstBarrier', 'executionExitUtc', 'realizedR',
      'minutesToFill', 'minutesInTrade', 'executionAuditStatus', 'executionAuditNotes'
    ];
    if (execKeys.some(function(k) { return Object.prototype.hasOwnProperty.call(u, k); })) {
      const execRange = sh.getRange(row, 122, 1, 8); // DR:DY
      const execCur = execRange.getValues()[0];
      function putExec(idx, key, numeric) {
        if (!Object.prototype.hasOwnProperty.call(u, key)) return;
        const v = u[key];
        if (v === null || typeof v === 'undefined') {
          execCur[idx] = '';
        } else if (numeric) {
          execCur[idx] = Number(v);
        } else {
          execCur[idx] = String(v);
        }
      }
      putExec(0, 'entryFilledUtc', false);
      putExec(1, 'firstBarrier', false);
      putExec(2, 'executionExitUtc', false);
      putExec(3, 'realizedR', true);
      putExec(4, 'minutesToFill', true);
      putExec(5, 'minutesInTrade', true);
      putExec(6, 'executionAuditStatus', false);
      putExec(7, 'executionAuditNotes', false);
      execRange.setValues([execCur]);
    }

    if (
      Object.prototype.hasOwnProperty.call(u, 'shadowTp1OneR') ||
      Object.prototype.hasOwnProperty.call(u, 'shadowTp1FirstBarrier') ||
      Object.prototype.hasOwnProperty.call(u, 'shadowTp1RealizedR')
    ) {
      const shadowRange = sh.getRange(row, 131, 1, 3); // EA:EC
      const shadowCur = shadowRange.getValues()[0];
      if (Object.prototype.hasOwnProperty.call(u, 'shadowTp1OneR')) {
        shadowCur[0] = u.shadowTp1OneR == null ? '' : Number(u.shadowTp1OneR);
      }
      if (Object.prototype.hasOwnProperty.call(u, 'shadowTp1FirstBarrier')) {
        shadowCur[1] = u.shadowTp1FirstBarrier == null ? '' : String(u.shadowTp1FirstBarrier);
      }
      if (Object.prototype.hasOwnProperty.call(u, 'shadowTp1RealizedR')) {
        shadowCur[2] = u.shadowTp1RealizedR == null ? '' : Number(u.shadowTp1RealizedR);
      }
      shadowRange.setValues([shadowCur]);
    }

    changed++;
  });

  return changed;
}

function appendAlertEvents_(ss, events) {
  if (!Array.isArray(events) || !events.length) return 0;

  const sh = sheet_(ss, 'ALERTS');
  const lastRow = sh.getLastRow();
  const existing = new Set();

  if (lastRow >= 2) {
    sh.getRange(2, 1, lastRow - 1, 1).getValues().forEach(function(r) {
      const id = String(r[0] || '');
      if (id) existing.add(id);
    });
  }

  const rows = [];
  events.forEach(function(e) {
    const id = String((e && e.id) || '');
    if (!id || existing.has(id)) return;
    rows.push([
      id,
      String(e.utc || ''),
      String(e.asset || ''),
      String(e.type || ''),
      String(e.signature || ''),
      e.telegramSent ? 'SI' : 'NO',
      String(e.message || '')
    ]);
    existing.add(id);
  });

  if (!rows.length) return 0;

  const startRow = sh.getLastRow() + 1;
  ensureRows_(sh, startRow + rows.length - 1);
  sh.getRange(startRow, 1, rows.length, 7).setValues(rows);

  const dataRows = sh.getLastRow() - 1;
  if (dataRows > MAX_RESEARCH_ROWS) {
    const excess = dataRows - MAX_RESEARCH_ROWS;
    sh.deleteRows(2, excess);
    sh.insertRowsAfter(sh.getMaxRows(), excess);
  }
  return rows.length;
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

    if (Array.isArray(payload.analysisUpdates)) {
      counts.ANALYSIS_UPDATES = applyAnalysisUpdates_(ss, payload.analysisUpdates);
    }

    if (Array.isArray(payload.alertEvents)) {
      counts.ALERT_EVENTS = appendAlertEvents_(ss, payload.alertEvents);
    }

    // Archivo de investigación separado: append-only y best-effort.
    // Un fallo del archivo NO debe interrumpir la alimentación operativa.
    let archiveCounts = {};
    let archiveError = '';
    try {
      archiveCounts = archiveResearch_(incomingSheets, payload.oi1m);
    } catch (archiveErr) {
      archiveError = String(
        archiveErr && archiveErr.message ? archiveErr.message : archiveErr
      );
      console.error('ARCHIVE falló: ' + archiveError);
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
      archiveRows: archiveCounts,
      archiveError: archiveError,
      openSignals: getOpenSignals_(ss),
      pendingAnalyses: getPendingAnalyses_(ss)
    });

  } catch (err) {
    return jsonOut_({
      ok: false,
      error: String(err && err.message ? err.message : err)
    });
  }
}

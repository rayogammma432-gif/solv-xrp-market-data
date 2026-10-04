// Receptor principal XRP V3.4. Sustituye operativamente V3.3 desde la activación V3.4.
// Receptor incremental 1m/5m/15m/1H/4H/1D para XRPUSDT
// + puente SIGNALS/PERFORMANCE para forward tracking.
// + XRP_FORWARD_V3 shadow append-only events/outcomes.
// El secreto NO se guarda en el código.
// Apps Script > Project Settings > Script properties:
// SHARED_SECRET = el mismo secreto que ya usa config.json en el Motorola.

const SPREADSHEET_ID = '1ag0yaE0hcDoG8uED4qejfHGlD2OuXZxvUPYZRUzjqG0';
const ARCHIVE_SPREADSHEET_ID = '12HcIA3AbJcQNTs9WGGNNouyIBpfzpk14MThPdeWMvZc';
const ASSET_SYMBOL = 'XRPUSDT';
const ASSET_PREFIX = 'XRP';
const XRP_V3_4_RECEPTOR_VERSION = 'XRP_RECEPTOR_V3_4_V1';
const XRP_V3_4_RULE_VERSION = 'XRP_V3.4';
const XRP_V3_4_SCHEMA_VERSION = 'XRP_V3_4_SCHEMA_DY_AQ_V1';
const SIGNAL_COLS = 43; // A:AQ (V3.4 adds Thesis/Rule/D/E/Gate)
const ANALYSIS_COLS = 129; // A:DY (V3.4 execution audit extends A:DJ)
const FORWARD_V3_EVENT_BASE_COLS = 27; // A:AA, receptor añade AB:AC
const FORWARD_V3_EVENT_COLS = 29; // A:AC
const FORWARD_V3_OUTCOME_BASE_COLS = 19; // A:S, receptor añade T:U
const FORWARD_V3_OUTCOME_COLS = 21; // A:U
const FORWARD_V3_HEALTH_BASE_COLS = 21; // A:U, receptor añade V:W
const FORWARD_V3_HEALTH_COLS = 23; // A:W
const FORWARD_V3_RECEPTOR_VERSION = 'XRP_RECEPTOR_FORWARD_V3_1_V1';
const PAIRED_CAPTURE_COLS = 21;
const PAIRED_SNAPSHOT_SEGMENT_COLS = 16;
const PAIRED_DECISION_COLS = 32;
const PAIRED_OUTCOME_COLS = 22;
const PAIRED_CAPTURE_BATCH = 'XRP_PAIR_POOL_V1';
const PAIRED_OUTCOME_VERSION = 'XRP_PAIRED_OUTCOME_V1';
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

// Security boundary for generic payload.sheets ingestion.
// Never allow a caller holding SHARED_SECRET to address operational/research tabs
// such as SIGNALS, ANALYSES, USER_TRADES, PERFORMANCE or PAIRED_* by name.
const XRP_BOOTSTRAP_INGESTION_SHEETS = Object.freeze([
  'XRP_1M', 'BTC_1M',
  'XRP_5M', 'BTC_5M',
  'XRP_15M', 'BTC_15M',
  'XRP_1H', 'BTC_1H',
  'XRP_4H', 'BTC_4H',
  'XRP_1D', 'BTC_1D'
]);
const XRP_INCREMENTAL_INGESTION_SHEETS = Object.freeze(
  XRP_BOOTSTRAP_INGESTION_SHEETS.concat([
    'ALERT_RESEARCH', 'ALERT_FORWARD', 'ALERT_MFE_MAE'
  ])
);

function validateIncomingSheets_(mode, incomingSheets) {
  if (
    incomingSheets === null ||
    typeof incomingSheets !== 'object' ||
    Array.isArray(incomingSheets)
  ) {
    throw new Error('payload.sheets debe ser un objeto');
  }
  const allowed = mode === 'bootstrap'
    ? XRP_BOOTSTRAP_INGESTION_SHEETS
    : XRP_INCREMENTAL_INGESTION_SHEETS;

  Object.keys(incomingSheets).forEach(function(name) {
    if (allowed.indexOf(name) === -1) {
      throw new Error('SHEET_NOT_ALLOWED mode=' + mode + ' sheet=' + name);
    }
    const rows = incomingSheets[name];
    if (!Array.isArray(rows)) {
      throw new Error('ROWS_NOT_ARRAY sheet=' + name);
    }
    rows.forEach(function(row, idx) {
      if (!Array.isArray(row) || row.length !== 11) {
        throw new Error(
          'ROW_WIDTH_INVALID sheet=' + name +
          ' row=' + idx +
          ' expected=11 received=' +
          (Array.isArray(row) ? row.length : 'NO_ARRAY')
        );
      }
    });
  });
  return incomingSheets;
}

function jsonOut_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function doGet(e) {
  return jsonOut_({
    ok: true,
    mode: 'HEALTH',
    receptorVersion: XRP_V3_4_RECEPTOR_VERSION,
    ruleVersion: XRP_V3_4_RULE_VERSION,
    schemaVersion: XRP_V3_4_SCHEMA_VERSION,
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
    XRP_1M: appendArchiveNew_(
      sheet_(archive, 'XRP_1M_ARCHIVE'),
      incomingSheets['XRP_1M'] || [],
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
      directionScore: String(r[40] || ''),
      executionScore: String(r[41] || ''),
      executionGate: String(r[42] || '')
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
      directionScore: String(r[114] || ''),
      executionScore: String(r[115] || ''),
      executionGate: String(r[116] || ''),
      planDirection: String(r[117] || ''),
      geometryValid: String(r[118] || ''),
      thesisId: String(r[119] || ''),
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

    // V3.4 deterministic plan validation: DN:DO.
    if (
      Object.prototype.hasOwnProperty.call(u, 'planDirection') ||
      Object.prototype.hasOwnProperty.call(u, 'geometryValid')
    ) {
      const planRange = sh.getRange(row, 118, 1, 2); // DN:DO
      const planCur = planRange.getValues()[0];
      if (Object.prototype.hasOwnProperty.call(u, 'planDirection')) {
        planCur[0] = u.planDirection == null ? '' : String(u.planDirection);
      }
      if (Object.prototype.hasOwnProperty.call(u, 'geometryValid')) {
        planCur[1] = u.geometryValid == null ? '' : String(u.geometryValid);
      }
      planRange.setValues([planCur]);
    }

    // V3.4 chronological execution audit: DQ:DX.
    const execKeys = [
      'entryFilledUtc', 'firstBarrier', 'executionExitUtc', 'realizedR',
      'minutesToFill', 'minutesInTrade', 'executionAuditStatus', 'executionAuditNotes'
    ];
    if (execKeys.some(function(k) { return Object.prototype.hasOwnProperty.call(u, k); })) {
      const execRange = sh.getRange(row, 121, 1, 8); // DQ:DX
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

function appendForwardRows_(sh, rows, baseCols, totalCols, receptorVersion) {
  if (!Array.isArray(rows) || !rows.length) return 0;

  const lastRow = sh.getLastRow();
  const existing = new Set();
  if (lastRow >= 2) {
    sh.getRange(2, 1, lastRow - 1, 1).getValues().forEach(function(r) {
      const id = String(r[0] || '');
      if (id) existing.add(id);
    });
  }

  const writeUtc = new Date().toISOString();
  const toAppend = [];
  rows.forEach(function(row) {
    if (!Array.isArray(row) || row.length !== baseCols) {
      throw new Error(
        'Fila Forward V3 con ancho inválido en ' + sh.getName() +
        ': esperado=' + baseCols + ' recibido=' +
        (Array.isArray(row) ? row.length : 'NO_ARRAY')
      );
    }
    const id = String(row[0] || '');
    if (!id || existing.has(id)) return;

    const stored = row.slice(0, baseCols);
    stored.push(String(receptorVersion || FORWARD_V3_RECEPTOR_VERSION));
    stored.push(writeUtc);
    if (stored.length !== totalCols) {
      throw new Error('Error interno de ancho Forward V3: ' + stored.length);
    }
    toAppend.push(stored);
    existing.add(id);
  });

  if (!toAppend.length) return 0;
  const startRow = sh.getLastRow() + 1;
  ensureRows_(sh, startRow + toAppend.length - 1);
  sh.getRange(startRow, 1, toAppend.length, totalCols).setValues(toAppend);
  return toAppend.length;
}

function appendForwardV3Events_(ss, rows) {
  return appendForwardRows_(
    sheet_(ss, 'FORWARD_V3_EVENTS'),
    rows,
    FORWARD_V3_EVENT_BASE_COLS,
    FORWARD_V3_EVENT_COLS,
    FORWARD_V3_RECEPTOR_VERSION
  );
}

function appendForwardV3Outcomes_(ss, rows) {
  return appendForwardRows_(
    sheet_(ss, 'FORWARD_V3_OUTCOMES'),
    rows,
    FORWARD_V3_OUTCOME_BASE_COLS,
    FORWARD_V3_OUTCOME_COLS,
    FORWARD_V3_RECEPTOR_VERSION
  );
}

function appendForwardV3Health_(ss, rows) {
  return appendForwardRows_(
    sheet_(ss, 'FORWARD_V3_HEALTH'),
    rows,
    FORWARD_V3_HEALTH_BASE_COLS,
    FORWARD_V3_HEALTH_COLS,
    FORWARD_V3_RECEPTOR_VERSION
  );
}

function sha256Hex_(text) {
  const bytes = Utilities.computeDigest(
    Utilities.DigestAlgorithm.SHA_256,
    String(text),
    Utilities.Charset.UTF_8
  );
  return bytes.map(function(b) {
    const v = b < 0 ? b + 256 : b;
    return ('0' + v.toString(16)).slice(-2);
  }).join('');
}

function appendPairedCaptures_(ss, alertRows, frozenUtc) {
  if (!Array.isArray(alertRows) || !alertRows.length) return 0;
  const sh = sheet_(ss, 'PAIRED_CAPTURES');
  const existing = new Set();
  const last = sh.getLastRow();
  if (last >= 2) {
    sh.getRange(2, 1, last - 1, 1).getValues().forEach(function(r) {
      const id = String(r[0] || '');
      if (id) existing.add(id);
    });
  }

  const nowIso = String(frozenUtc || new Date().toISOString());
  const rows = [];
  alertRows.forEach(function(src) {
    if (!Array.isArray(src) || src.length < 11) return;
    const pairId = String(src[2] || '');
    if (!pairId || existing.has(pairId)) return;
    const canonical = JSON.stringify(src.slice(0, 11));
    rows.push([
      pairId,
      String(src[0] || ''),
      String(src[1] || ''),
      pairId,
      String(src[3] || ''),
      String(src[4] || ''),
      String(src[5] || ''),
      src[6] === '' ? '' : Number(src[6]),
      String(src[7] || ''),
      String(src[8] || ''),
      String(src[9] || ''),
      String(src[10] || ''),
      'ALERT_RESEARCH',
      nowIso,
      PAIRED_CAPTURE_BATCH,
      'PRELAUNCH_POOL',
      sha256Hex_(canonical),
      '',
      'RESEARCH_ONLY',
      'ALERT_RESEARCH_ONLY_V1',
      'Legacy/supportive capture; full bar snapshot not frozen.'
    ]);
    existing.add(pairId);
  });

  if (!rows.length) return 0;
  const startRow = sh.getLastRow() + 1;
  ensureRows_(sh, startRow + rows.length - 1);
  sh.getRange(startRow, 1, rows.length, PAIRED_CAPTURE_COLS).setValues(rows);
  return rows.length;
}

function backfillPairedCapturesFromAlertResearch_(ssOpt) {
  const ss = ssOpt || SpreadsheetApp.openById(SPREADSHEET_ID);
  const src = sheet_(ss, 'ALERT_RESEARCH');
  const last = src.getLastRow();
  if (last < 2) return 0;
  const rows = src.getRange(2, 1, last - 1, 11).getValues();
  return appendPairedCaptures_(ss, rows, new Date().toISOString());
}

function appendPairedCaptureBundles_(ss, bundles) {
  if (!Array.isArray(bundles) || !bundles.length) return {captures:0, segments:0};

  const capSh = sheet_(ss, 'PAIRED_CAPTURES');
  const segSh = sheet_(ss, 'PAIRED_SNAPSHOT_BARS');

  const capRowById = {};
  if (capSh.getLastRow() >= 2) {
    capSh.getRange(2, 1, capSh.getLastRow() - 1, PAIRED_CAPTURE_COLS)
      .getValues().forEach(function(r, i) {
        const id = String(r[0] || '');
        if (id) capRowById[id] = i + 2;
      });
  }
  const segExisting = new Set();
  if (segSh.getLastRow() >= 2) {
    segSh.getRange(2, 1, segSh.getLastRow() - 1, 1).getValues().forEach(function(r) {
      const id = String(r[0] || '');
      if (id) segExisting.add(id);
    });
  }

  let capWrites = 0;
  const segRows = [];
  bundles.forEach(function(b) {
    const cap = b && Array.isArray(b.capture) ? b.capture : null;
    const segs = b && Array.isArray(b.segments) ? b.segments : [];
    if (!cap || cap.length !== PAIRED_CAPTURE_COLS) {
      throw new Error('paired capture bundle inválido');
    }
    const pairId = String(cap[0] || '');
    if (!pairId) throw new Error('paired capture sin Pair ID');

    const segShas = [];
    const seenSegmentIds = new Set();
    const series = {};
    segs.forEach(function(seg) {
      if (!Array.isArray(seg) || seg.length !== PAIRED_SNAPSHOT_SEGMENT_COLS) {
        throw new Error('paired snapshot segment inválido');
      }
      if (String(seg[1] || '') !== pairId || String(seg[2] || '') !== pairId) {
        throw new Error('paired snapshot Pair ID inconsistente: ' + pairId);
      }
      const segId = String(seg[0] || '');
      if (!segId || seenSegmentIds.has(segId)) {
        throw new Error('segmento duplicado/sin ID: ' + pairId);
      }
      seenSegmentIds.add(segId);

      const key = String(seg[3] || '') + '|' + String(seg[4] || '');
      const chunkIndex = Number(seg[5]);
      const chunkCount = Number(seg[6]);
      const expectedTotal = Number(seg[9]);
      const chunkBars = Number(seg[10]);
      if (
        !Number.isInteger(chunkIndex) || !Number.isInteger(chunkCount) ||
        chunkIndex < 1 || chunkCount < 1 || chunkIndex > chunkCount ||
        !Number.isInteger(expectedTotal) || expectedTotal < 1 ||
        !Number.isInteger(chunkBars) || chunkBars < 0
      ) {
        throw new Error('metadata de chunk inválida: ' + pairId + ' ' + key);
      }

      const cutoff = Date.parse(String(seg[8] || ''));
      const alertTs = Date.parse(String(cap[2] || ''));
      const segAlertTs = Date.parse(String(seg[7] || ''));
      if (
        !isFinite(cutoff) || !isFinite(alertTs) || !isFinite(segAlertTs) ||
        cutoff > alertTs || segAlertTs !== alertTs
      ) {
        throw new Error('look-ahead/timestamp inconsistente: ' + pairId + ' ' + key);
      }

      const barsJson = String(seg[12] || '');
      if (barsJson.length > 48000) {
        throw new Error('Bars JSON excede límite seguro de celda: ' + pairId + ' ' + key);
      }
      let parsedBars;
      try {
        parsedBars = JSON.parse(barsJson);
      } catch (e) {
        throw new Error('Bars JSON inválido: ' + pairId + ' ' + key);
      }
      if (!Array.isArray(parsedBars) || parsedBars.length !== chunkBars) {
        throw new Error('conteo de barras de chunk inconsistente: ' + pairId + ' ' + key);
      }

      const group = series[key] || {
        chunkCount: chunkCount,
        expectedTotal: expectedTotal,
        barTotal: 0,
        indexes: new Set(),
        barsByChunk: {},
        allFull: true
      };
      if (group.chunkCount !== chunkCount || group.expectedTotal !== expectedTotal) {
        throw new Error('metadata de serie inconsistente: ' + pairId + ' ' + key);
      }
      if (group.indexes.has(chunkIndex)) {
        throw new Error('chunk index duplicado: ' + pairId + ' ' + key);
      }
      group.indexes.add(chunkIndex);
      group.barsByChunk[chunkIndex] = parsedBars;
      group.barTotal += chunkBars;
      group.allFull = group.allFull && String(seg[11] || '') === 'FULL';
      series[key] = group;

      if (String(seg[14] || '') !== 'XRP_PAIRED_SNAPSHOT_V1') {
        throw new Error('snapshot version de segmento inválida: ' + pairId + ' ' + key);
      }
      segShas.push(String(seg[13] || ''));
    });

    const seriesKeys = Object.keys(series);
    if (seriesKeys.length !== 12) {
      throw new Error('paired snapshot requiere 12 series lógicas: ' + pairId);
    }
    seriesKeys.forEach(function(key) {
      const g = series[key];
      if (g.indexes.size !== g.chunkCount || g.barTotal !== g.expectedTotal) {
        throw new Error('serie chunked incompleta: ' + pairId + ' ' + key);
      }
      for (let i = 1; i <= g.chunkCount; i++) {
        if (!g.indexes.has(i)) {
          throw new Error('falta chunk ' + i + ': ' + pairId + ' ' + key);
        }
      }
      const tf = key.split('|')[1];
      const tfMs = {
        '1m':60000, '5m':300000, '15m':900000,
        '1h':3600000, '4h':14400000, '1d':86400000
      }[tf];
      if (!tfMs) throw new Error('timeframe paired desconocido: ' + tf);
      let assembled = [];
      for (let i = 1; i <= g.chunkCount; i++) {
        assembled = assembled.concat(g.barsByChunk[i] || []);
      }
      if (assembled.length !== g.expectedTotal) {
        throw new Error('serie reconstruida con conteo inválido: ' + pairId + ' ' + key);
      }
      for (let i = 0; i < assembled.length; i++) {
        const bar = assembled[i];
        if (!Array.isArray(bar) || bar.length < 7) {
          throw new Error('barra paired inválida: ' + pairId + ' ' + key);
        }
        const om = Number(bar[0]), cm = Number(bar[6]);
        if (!isFinite(om) || !isFinite(cm) || cm > Date.parse(String(cap[2] || ''))) {
          throw new Error('barra paired con look-ahead/timestamp inválido: ' + pairId + ' ' + key);
        }
        if (i > 0 && om - Number(assembled[i-1][0]) !== tfMs) {
          throw new Error('gap en paired snapshot: ' + pairId + ' ' + key);
        }
      }
      const alertTs = Date.parse(String(cap[2] || ''));
      const expectedLastClose = Math.floor(alertTs / tfMs) * tfMs - 1;
      if (Number(assembled[assembled.length - 1][6]) !== expectedLastClose) {
        throw new Error('paired snapshot stale/no exact latest close: ' + pairId + ' ' + key);
      }
      if (String(cap[15] || '').toUpperCase() === 'FORMAL_PROSPECTIVE' && !g.allFull) {
        throw new Error('serie formal PARTIAL: ' + pairId + ' ' + key);
      }
    });

    const calculatedFullSha = sha256Hex_(
      String(cap[16] || '') + '|' + segShas.slice().sort().join('|')
    );
    if (!String(cap[17] || '') || calculatedFullSha !== String(cap[17] || '')) {
      throw new Error('Full Snapshot SHA256 inválido: ' + pairId);
    }
    if (String(cap[15] || '').toUpperCase() === 'FORMAL_PROSPECTIVE') {
      if (String(cap[18] || '') !== 'FULL' || String(cap[19] || '') !== 'XRP_PAIRED_SNAPSHOT_V1') {
        throw new Error('snapshot formal incompleto/version inválida: ' + pairId);
      }
    }

    const existingRow = capRowById[pairId];
    if (existingRow) {
      const current = capSh.getRange(existingRow, 1, 1, PAIRED_CAPTURE_COLS).getValues()[0];
      const currentCompleteness = String(current[18] || '');
      if (currentCompleteness !== 'FULL' && String(cap[18] || '') === 'FULL') {
        capSh.getRange(existingRow, 1, 1, PAIRED_CAPTURE_COLS).setValues([cap]);
        capWrites += 1;
      }
    } else {
      const row = capSh.getLastRow() + 1;
      ensureRows_(capSh, row);
      capSh.getRange(row, 1, 1, PAIRED_CAPTURE_COLS).setValues([cap]);
      capRowById[pairId] = row;
      capWrites += 1;
    }

    segs.forEach(function(seg) {
      if (!Array.isArray(seg) || seg.length !== PAIRED_SNAPSHOT_SEGMENT_COLS) {
        throw new Error('paired snapshot segment inválido');
      }
      const segId = String(seg[0] || '');
      if (!segId || segExisting.has(segId)) return;
      segRows.push(seg);
      segExisting.add(segId);
    });
  });

  if (segRows.length) {
    const startRow = segSh.getLastRow() + 1;
    ensureRows_(segSh, startRow + segRows.length - 1);
    segSh.getRange(startRow, 1, segRows.length, PAIRED_SNAPSHOT_SEGMENT_COLS).setValues(segRows);
  }
  return {captures:capWrites, segments:segRows.length};
}

function _decisionPairIds_(sh) {
  const out = new Set();
  const last = sh.getLastRow();
  if (last < 2) return out;
  sh.getRange(2, 1, last - 1, PAIRED_DECISION_COLS).getValues().forEach(function(r) {
    if (String(r[28] || '').toUpperCase() !== 'COMPLETE') return;
    const pairId = String(r[1] || '');
    if (pairId) out.add(pairId);
  });
  return out;
}

function buildPairedOutcomes_(ssOpt) {
  const ss = ssOpt || SpreadsheetApp.openById(SPREADSHEET_ID);
  const currentIds = _decisionPairIds_(sheet_(ss, 'PAIRED_CURRENT'));
  const challengerIds = _decisionPairIds_(sheet_(ss, 'PAIRED_CHALLENGER'));

  const captureSh = sheet_(ss, 'PAIRED_CAPTURES');
  const captures = {};
  if (captureSh.getLastRow() >= 2) {
    captureSh.getRange(2, 1, captureSh.getLastRow() - 1, PAIRED_CAPTURE_COLS)
      .getValues().forEach(function(r) {
        const id = String(r[0] || '');
        if (id) captures[id] = r;
      });
  }

  const fwdSh = sheet_(ss, 'ALERT_FORWARD');
  const fwd = {};
  if (fwdSh.getLastRow() >= 2) {
    fwdSh.getRange(2, 1, fwdSh.getLastRow() - 1, 11).getValues().forEach(function(r) {
      const id = String(r[1] || '');
      if (id) fwd[id] = r;
    });
  }

  const mfeSh = sheet_(ss, 'ALERT_MFE_MAE');
  const mfe = {};
  if (mfeSh.getLastRow() >= 2) {
    mfeSh.getRange(2, 1, mfeSh.getLastRow() - 1, 11).getValues().forEach(function(r) {
      const id = String(r[1] || '');
      if (id) mfe[id] = r;
    });
  }

  const outSh = sheet_(ss, 'PAIRED_OUTCOMES');
  const existing = new Set();
  if (outSh.getLastRow() >= 2) {
    outSh.getRange(2, 1, outSh.getLastRow() - 1, 1).getValues().forEach(function(r) {
      const id = String(r[0] || '');
      if (id) existing.add(id);
    });
  }

  const rows = [];
  Object.keys(captures).sort().forEach(function(pairId) {
    if (existing.has(pairId)) return;
    if (!currentIds.has(pairId) || !challengerIds.has(pairId)) return;
    const cap = captures[pairId];
    const fr = fwd[pairId];
    const mr = mfe[pairId];
    if (!fr || !mr) return;

    const det = String(cap[6] || '').toUpperCase();
    if (det !== 'LONG' && det !== 'SHORT') return;
    const sign = det === 'LONG' ? 1 : -1;

    function n(v) {
      if (v === '' || v === null || typeof v === 'undefined') return null;
      const x = Number(v);
      return isFinite(x) ? x : null;
    }
    const f5=n(fr[6]),f15=n(fr[7]),f30=n(fr[8]),f60=n(fr[9]),f240=n(fr[10]);
    const m15=n(mr[5]),a15=n(mr[6]),m60=n(mr[7]),a60=n(mr[8]),m240=n(mr[9]),a240=n(mr[10]);
    const vals=[f5,f15,f30,f60,f240,m15,a15,m60,a60,m240,a240];
    if (vals.some(function(x){return x===null;})) return;

    function rawPair(m, a) {
      return det === 'LONG' ? [m, -a] : [a, -m];
    }
    const e15=rawPair(m15,a15),e60=rawPair(m60,a60),e240=rawPair(m240,a240);

    rows.push([
      pairId,
      pairId,
      String(cap[2] || ''),
      det,
      cap[7] === '' ? '' : Number(cap[7]),
      sign*f5,
      sign*f15,
      sign*f30,
      sign*f60,
      sign*f240,
      e15[0],e15[1],
      e60[0],e60[1],
      e240[0],e240[1],
      String(fr[0] || ''),
      String(mr[0] || ''),
      'COMPLETE',
      PAIRED_OUTCOME_VERSION,
      new Date().toISOString(),
      'Direction-neutral reconstruction after both arm decisions were COMPLETE.'
    ]);
    existing.add(pairId);
  });

  if (!rows.length) return 0;
  const start=outSh.getLastRow()+1;
  ensureRows_(outSh,start+rows.length-1);
  outSh.getRange(start,1,rows.length,PAIRED_OUTCOME_COLS).setValues(rows);
  return rows.length;
}

function getForwardV3Recovery_(ss) {
  const eventsSh = sheet_(ss, 'FORWARD_V3_EVENTS');
  const outcomesSh = sheet_(ss, 'FORWARD_V3_OUTCOMES');
  const healthSh = sheet_(ss, 'FORWARD_V3_HEALTH');

  const eventCount = Math.max(0, eventsSh.getLastRow() - 1);
  const eventTake = Math.min(eventCount, 1200);
  const events = eventTake
    ? eventsSh.getRange(eventsSh.getLastRow() - eventTake + 1, 1, eventTake, FORWARD_V3_EVENT_COLS).getValues()
    : [];

  const outcomeCount = Math.max(0, outcomesSh.getLastRow() - 1);
  const outcomeTake = Math.min(outcomeCount, 9000);
  const outcomeIds = outcomeTake
    ? outcomesSh.getRange(outcomesSh.getLastRow() - outcomeTake + 1, 1, outcomeTake, 1).getValues().map(function(r) {
        return String(r[0] || '');
      }).filter(Boolean)
    : [];

  let latestHealth = null;
  if (healthSh.getLastRow() >= 2) {
    latestHealth = healthSh.getRange(
      healthSh.getLastRow(), 1, 1, FORWARD_V3_HEALTH_COLS
    ).getValues()[0];
  }

  return {
    receptorVersion: FORWARD_V3_RECEPTOR_VERSION,
    events: events,
    outcomeIds: outcomeIds,
    latestHealth: latestHealth
  };
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
    const incomingSheets = validateIncomingSheets_(mode, payload.sheets || {});

    const ss = SpreadsheetApp.openById(SPREADSHEET_ID);
    const counts = {};

    Object.keys(incomingSheets).forEach(function(name) {
      const rows = incomingSheets[name];
      const sh = sheet_(ss, name);
      const maxRows = maxForSheet_(name);
      if (mode === 'bootstrap') {
        counts[name] = fullReplace_(sh, rows, 11, maxRows);
      } else {
        counts[name] = appendNew_(sh, rows, 11, maxRows);
      }
      // PAIRED_CAPTURES prospectivos se escriben desde pairedCaptureBundles
      // para garantizar snapshot de barras completo.
    });

    if (mode === 'bootstrap') {
      counts.PAIRED_CAPTURES_BACKFILL = backfillPairedCapturesFromAlertResearch_(ss);
    }

    if (Array.isArray(payload.pairedCaptureBundles)) {
      const pc = appendPairedCaptureBundles_(ss, payload.pairedCaptureBundles);
      counts.PAIRED_CAPTURES_FULL = pc.captures;
      counts.PAIRED_SNAPSHOT_BARS = pc.segments;
    }

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

    // Forward V3 shadow research: append-only + deterministic ID dedupe.
    // Never touches SIGNALS, ANALYSES, USER_TRADES or operational state.
    if (Array.isArray(payload.forwardV3Events)) {
      counts.FORWARD_V3_EVENTS = appendForwardV3Events_(ss, payload.forwardV3Events);
    }

    if (Array.isArray(payload.forwardV3Outcomes)) {
      counts.FORWARD_V3_OUTCOMES = appendForwardV3Outcomes_(ss, payload.forwardV3Outcomes);
    }

    if (Array.isArray(payload.forwardV3Health)) {
      counts.FORWARD_V3_HEALTH = appendForwardV3Health_(ss, payload.forwardV3Health);
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

    const recovery = payload.forwardV3RecoveryRequest
      ? getForwardV3Recovery_(ss)
      : null;

    return jsonOut_({
      ok: true,
      status: 'OK',
      mode: mode,
      updatedAtUtc: payload.generatedAtUtc || new Date().toISOString(),
      rows: counts,
      archiveRows: archiveCounts,
      archiveError: archiveError,
      openSignals: getOpenSignals_(ss),
      pendingAnalyses: getPendingAnalyses_(ss),
      receptorVersion: FORWARD_V3_RECEPTOR_VERSION,
      xrpV34ReceptorVersion: XRP_V3_4_RECEPTOR_VERSION,
      xrpV34RuleVersion: XRP_V3_4_RULE_VERSION,
      xrpV34SchemaVersion: XRP_V3_4_SCHEMA_VERSION,
      forwardV3Recovery: recovery
    });

  } catch (err) {
    return jsonOut_({
      ok: false,
      error: String(err && err.message ? err.message : err)
    });
  }
}

// Dedicated XRP Challenger research receptor.
// Deploy as a separate Apps Script web app from the operational XRP receptor.
// Script property required:
// CHALLENGER_SHARED_SECRET = secret used only by termux challenger config.

const CHALLENGER_SPREADSHEET_ID = '14mVe2XXcsVBCojZSbp6A7qQKO2RFpovLtKntOYFDwvA';
const CHALLENGER_RECEPTOR_VERSION = 'XRP_RECEPTOR_CHALLENGER_V2_R3';
const CHALLENGER_RECEPTOR_BUILD_ID = 'XRP_CHALLENGER_RECEPTOR_BUILD_20261002_R3';
const EXPECTED_PROTOCOL_VERSION = 'XRP_FORWARD_V3_2';
const EXPECTED_REGISTRY_SHA256 = '99c17ecf3c3b376f734dc7469351445c7d6727f96d0cb7d5580ea59b5f9f932a';
const EXPECTED_COLLECTOR_VERSION = 'XRP_CHALLENGER_COLLECTOR_V2_R2';

const EVENT_BASE_COLS = 27;
const EVENT_COLS = 29;
const OUTCOME_BASE_COLS = 19;
const OUTCOME_COLS = 21;
const HEALTH_BASE_COLS = 21;
const HEALTH_COLS = 23;
const AUDIT_COLS = 9;

function jsonOut_(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function sheet_(ss, name) {
  const sh = ss.getSheetByName(name);
  if (!sh) throw new Error('Falta la pestaña Challenger: ' + name);
  return sh;
}

function ensureRows_(sh, neededLastRow) {
  if (sh.getMaxRows() < neededLastRow) {
    sh.insertRowsAfter(sh.getMaxRows(), neededLastRow - sh.getMaxRows());
  }
}

function appendUniqueResearchRows_(sh, rows, baseCols, totalCols) {
  if (!Array.isArray(rows) || !rows.length) return 0;

  const existing = new Map();
  const last = sh.getLastRow();
  if (last >= 2) {
    const n = last - 1;
    const ids = sh.getRange(2, 1, n, 1).getValues();
    const hashes = sh.getRange(2, baseCols, n, 1).getValues();
    for (let i = 0; i < n; i++) {
      const id = String(ids[i][0] || '');
      const payloadHash = String(hashes[i][0] || '');
      if (id) existing.set(id, payloadHash);
    }
  }

  const writeUtc = new Date().toISOString();
  const out = [];
  rows.forEach(function(row) {
    if (!Array.isArray(row) || row.length !== baseCols) {
      throw new Error(
        'Ancho Challenger inválido en ' + sh.getName() +
        ': esperado=' + baseCols +
        ' recibido=' + (Array.isArray(row) ? row.length : 'NO_ARRAY')
      );
    }
    const id = String(row[0] || '');
    if (!id) throw new Error('ID Challenger vacío en ' + sh.getName());
    const incomingHash = String(row[baseCols - 1] || '');
    if (!incomingHash) {
      throw new Error('Payload SHA256 vacío para ' + id);
    }
    if (existing.has(id)) {
      const storedHash = String(existing.get(id) || '');
      if (storedHash !== incomingHash) {
        throw new Error(
          'IDEMPOTENCY_CONFLICT id=' + id +
          ' stored_hash=' + storedHash +
          ' incoming_hash=' + incomingHash
        );
      }
      return;
    }
    const stored = row.slice();
    stored.push(CHALLENGER_RECEPTOR_VERSION);
    stored.push(writeUtc);
    if (stored.length !== totalCols) {
      throw new Error('Ancho almacenado Challenger inválido: ' + stored.length);
    }
    out.push(stored);
    existing.set(id, incomingHash);
  });

  if (!out.length) return 0;
  const start = sh.getLastRow() + 1;
  ensureRows_(sh, start + out.length - 1);
  sh.getRange(start, 1, out.length, totalCols).setValues(out);
  return out.length;
}

function validateCandidateRows_(rows) {
  (rows || []).forEach(function(row) {
    if (
      String(row[1] || '') !== EXPECTED_PROTOCOL_VERSION ||
      String(row[20] || '') !== EXPECTED_REGISTRY_SHA256 ||
      String(row[23] || '') !== EXPECTED_COLLECTOR_VERSION
    ) {
      throw new Error('Candidate provenance/version mismatch');
    }
  });
}

function validateOutcomeRows_(rows) {
  (rows || []).forEach(function(row) {
    if (
      String(row[13] || '') !== EXPECTED_REGISTRY_SHA256 ||
      String(row[14] || '') !== EXPECTED_COLLECTOR_VERSION
    ) {
      throw new Error('Outcome provenance/version mismatch');
    }
  });
}

function validateHealthRows_(rows) {
  (rows || []).forEach(function(row) {
    if (
      String(row[1] || '') !== EXPECTED_PROTOCOL_VERSION ||
      String(row[18] || '') !== EXPECTED_COLLECTOR_VERSION
    ) {
      throw new Error('Health provenance/version mismatch');
    }
  });
}

function appendAudit_(ss, rows) {
  if (!Array.isArray(rows) || !rows.length) return 0;
  const sh = sheet_(ss, 'CHALLENGER_AUDIT');
  const existing = new Set();
  const last = sh.getLastRow();
  if (last >= 2) {
    sh.getRange(2, 1, last - 1, 1).getValues().forEach(function(r) {
      const id = String(r[0] || '');
      if (id) existing.add(id);
    });
  }
  const out = [];
  rows.forEach(function(row) {
    if (!Array.isArray(row) || row.length !== AUDIT_COLS) {
      throw new Error('Ancho CHALLENGER_AUDIT inválido');
    }
    const id = String(row[0] || '');
    if (!id || existing.has(id)) return;
    out.push(row.slice());
    existing.add(id);
  });
  if (!out.length) return 0;
  const start = sh.getLastRow() + 1;
  ensureRows_(sh, start + out.length - 1);
  sh.getRange(start, 1, out.length, AUDIT_COLS).setValues(out);
  return out.length;
}

function requiredHorizons_(candidateId) {
  if (candidateId === 'XRP-FWD-V3-A-TAKER-EXHAUSTION') return [5, 15, 30];
  if (candidateId === 'XRP-FWD-V3-B-OI-MODERATOR') return [60];
  if (candidateId === 'XRP-FWD-V3-C-MOMENTUM-EXHAUSTION') return [15, 60, 240];
  return [];
}

function fetchRowsByNumbers_(sh, rowNumbers, width) {
  if (!rowNumbers.length) return [];
  const rows = [];
  let start = rowNumbers[0];
  let prev = start;

  function flush_(a, b) {
    const vals = sh.getRange(a, 1, b - a + 1, width).getValues();
    vals.forEach(function(row) { rows.push(row); });
  }

  for (let i = 1; i < rowNumbers.length; i++) {
    const n = rowNumbers[i];
    if (n === prev + 1) {
      prev = n;
      continue;
    }
    flush_(start, prev);
    start = n;
    prev = n;
  }
  flush_(start, prev);
  return rows;
}

function recovery_(ss) {
  const eventsSh = sheet_(ss, 'CHALLENGER_CANDIDATES');
  const outcomesSh = sheet_(ss, 'CHALLENGER_OUTCOMES');
  const healthSh = sheet_(ss, 'CHALLENGER_HEALTH');

  let latestHealth = null;
  let recoveryFloor = '';
  if (healthSh.getLastRow() >= 2) {
    latestHealth = healthSh.getRange(
      healthSh.getLastRow(),
      1,
      1,
      HEALTH_COLS
    ).getValues()[0];

    const last1 = String(latestHealth[16] || '');
    const last15 = String(latestHealth[17] || '');
    if (last1 && last15) recoveryFloor = last1 < last15 ? last1 : last15;
    else recoveryFloor = last1 || last15 || '';
  }

  const outcomesByEvent = new Map();
  const outcomeIdByEventHorizon = new Map();
  const outcomeCount = Math.max(0, outcomesSh.getLastRow() - 1);
  if (outcomeCount) {
    const outcomeMeta = outcomesSh.getRange(2, 1, outcomeCount, 5).getValues();
    outcomeMeta.forEach(function(row) {
      const outcomeId = String(row[0] || '');
      const eventId = String(row[1] || '');
      const horizon = Number(row[4]);
      if (!eventId || !Number.isFinite(horizon)) return;
      if (!outcomesByEvent.has(eventId)) outcomesByEvent.set(eventId, new Set());
      outcomesByEvent.get(eventId).add(horizon);
      outcomeIdByEventHorizon.set(eventId + '|' + horizon, outcomeId);
    });
  }

  const selectedRows = [];
  const selectedEventIds = new Set();
  const eventCount = Math.max(0, eventsSh.getLastRow() - 1);
  if (eventCount) {
    const eventMeta = eventsSh.getRange(2, 1, eventCount, 6).getValues();
    eventMeta.forEach(function(row, i) {
      const eventId = String(row[0] || '');
      const protocol = String(row[1] || '');
      const candidateId = String(row[2] || '');
      const decisionTime = String(row[5] || '');
      if (!eventId || protocol !== EXPECTED_PROTOCOL_VERSION) return;

      const required = requiredHorizons_(candidateId);
      if (!required.length) return;
      const have = outcomesByEvent.get(eventId) || new Set();
      const pending = required.some(function(h) { return !have.has(h); });
      const newerThanCheckpoint = !recoveryFloor || (decisionTime && decisionTime > recoveryFloor);

      if (pending || newerThanCheckpoint) {
        selectedRows.push(i + 2);
        selectedEventIds.add(eventId);
      }
    });
  }

  const events = fetchRowsByNumbers_(eventsSh, selectedRows, EVENT_COLS);
  const outcomeIds = [];
  selectedEventIds.forEach(function(eventId) {
    const have = outcomesByEvent.get(eventId) || new Set();
    have.forEach(function(h) {
      const oid = outcomeIdByEventHorizon.get(eventId + '|' + h);
      if (oid) outcomeIds.push(oid);
    });
  });

  return {
    receptorVersion: CHALLENGER_RECEPTOR_VERSION,
    recoveryMode: 'PENDING_OUTCOMES_PLUS_POST_CHECKPOINT',
    recoveryFloorUtc: recoveryFloor,
    events: events,
    outcomeIds: outcomeIds,
    latestHealth: latestHealth
  };
}

function doPost(e) {
  try {
    const expected = PropertiesService
      .getScriptProperties()
      .getProperty('CHALLENGER_SHARED_SECRET');

    if (!expected) {
      throw new Error('Falta Script Property CHALLENGER_SHARED_SECRET');
    }

    const body = e && e.postData && e.postData.contents
      ? e.postData.contents
      : '{}';
    const payload = JSON.parse(body);

    if (String(payload.secret || '') !== String(expected)) {
      return jsonOut_({ok:false, error:'UNAUTHORIZED'});
    }

    const mode = String(payload.mode || '').toLowerCase();
    if (
      mode !== 'challenger_recovery' &&
      mode !== 'challenger_incremental'
    ) {
      throw new Error('mode Challenger inválido: ' + mode);
    }

    const lock = LockService.getScriptLock();
    if (!lock.tryLock(30000)) {
      throw new Error('CHALLENGER_WRITE_LOCK_TIMEOUT');
    }

    try {
      const ss = SpreadsheetApp.openById(CHALLENGER_SPREADSHEET_ID);
      const counts = {};

    if (Array.isArray(payload.challengerCandidates)) {
      validateCandidateRows_(payload.challengerCandidates);
      counts.CHALLENGER_CANDIDATES = appendUniqueResearchRows_(
        sheet_(ss, 'CHALLENGER_CANDIDATES'),
        payload.challengerCandidates,
        EVENT_BASE_COLS,
        EVENT_COLS
      );
    }

    if (Array.isArray(payload.challengerOutcomes)) {
      validateOutcomeRows_(payload.challengerOutcomes);
      counts.CHALLENGER_OUTCOMES = appendUniqueResearchRows_(
        sheet_(ss, 'CHALLENGER_OUTCOMES'),
        payload.challengerOutcomes,
        OUTCOME_BASE_COLS,
        OUTCOME_COLS
      );
    }

    if (Array.isArray(payload.challengerHealth)) {
      validateHealthRows_(payload.challengerHealth);
      counts.CHALLENGER_HEALTH = appendUniqueResearchRows_(
        sheet_(ss, 'CHALLENGER_HEALTH'),
        payload.challengerHealth,
        HEALTH_BASE_COLS,
        HEALTH_COLS
      );
    }

    if (Array.isArray(payload.challengerAudit)) {
      counts.CHALLENGER_AUDIT = appendAudit_(
        ss,
        payload.challengerAudit
      );
    }

    SpreadsheetApp.flush();

    const recovery = payload.challengerRecoveryRequest
      ? recovery_(ss)
      : null;

      return jsonOut_({
        ok: true,
        status: 'OK',
        mode: mode,
        updatedAtUtc: payload.generatedAtUtc || new Date().toISOString(),
        rows: counts,
        challengerReceptorVersion: CHALLENGER_RECEPTOR_VERSION,
        challengerReceptorBuildId: CHALLENGER_RECEPTOR_BUILD_ID,
        challengerSpreadsheetId: CHALLENGER_SPREADSHEET_ID,
        challengerProtocolVersion: EXPECTED_PROTOCOL_VERSION,
        challengerRegistrySha256: EXPECTED_REGISTRY_SHA256,
        challengerCollectorVersion: EXPECTED_COLLECTOR_VERSION,
        challengerRecovery: recovery
      });
    } finally {
      lock.releaseLock();
    }

  } catch (err) {
    return jsonOut_({
      ok: false,
      error: String(err && err.message ? err.message : err)
    });
  }
}

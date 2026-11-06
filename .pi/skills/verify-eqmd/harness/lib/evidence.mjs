// Evidence helpers: every helper and journey appends to the same run directory.
import fs from 'node:fs';
import path from 'node:path';

import { EVIDENCE_DIR, RUN_ID } from './config.mjs';

export function ensureEvidence() {
  fs.mkdirSync(EVIDENCE_DIR, { recursive: true });
  return EVIDENCE_DIR;
}

export function evidencePath(...segments) {
  const target = path.join(EVIDENCE_DIR, ...segments);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  return target;
}

export function writeJson(relativePath, data) {
  const target = evidencePath(relativePath);
  fs.writeFileSync(target, JSON.stringify(data, null, 2) + '\n', 'utf8');
  return target;
}

export function readJson(relativePath) {
  const target = path.join(EVIDENCE_DIR, relativePath);
  if (!fs.existsSync(target)) {
    throw new Error(
      `missing evidence file ${target}; run "npm run setup" (and "npm run doctor") first`,
    );
  }
  return JSON.parse(fs.readFileSync(target, 'utf8'));
}

/**
 * Append one command/helper outcome to the run's command log.
 * The log is JSON Lines so the final report can quote it verbatim.
 */
export function logCommand({ helper, argv = [], exitCode = 0, durationMs = 0, note = '', stdoutTail = '' }) {
  ensureEvidence();
  const entry = {
    ts: new Date().toISOString(),
    runId: RUN_ID,
    helper,
    argv,
    exitCode,
    durationMs,
    note,
    stdoutTail: stdoutTail.split('\n').slice(-12).join('\n'),
  };
  fs.appendFileSync(path.join(EVIDENCE_DIR, 'command-log.jsonl'), JSON.stringify(entry) + '\n', 'utf8');
  return entry;
}

export function requireScaffold() {
  return readJson('scaffold.json');
}

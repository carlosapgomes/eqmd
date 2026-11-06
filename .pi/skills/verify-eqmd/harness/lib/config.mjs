// Run configuration shared by every helper and journey script.
// Everything is env-overridable so the skill works from any worktree copy.
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));

export const HARNESS_DIR = path.resolve(HERE, '..');
export const SKILL_DIR = path.resolve(HARNESS_DIR, '..');
export const REPO_ROOT = path.resolve(SKILL_DIR, '../../..');

export const BASE_URL = process.env.EQMD_VERIFY_BASE_URL || 'http://127.0.0.1:8779';
export const CONTAINER = process.env.EQMD_VERIFY_CONTAINER || 'eqmd_dev';

function defaultRunId() {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  return [
    now.getFullYear(),
    pad(now.getMonth() + 1),
    pad(now.getDate()),
    '-',
    pad(now.getHours()),
    pad(now.getMinutes()),
    pad(now.getSeconds()),
  ].join('');
}

export const RUN_ID = process.env.EQMD_VERIFY_RUN_ID || defaultRunId();
export const EVIDENCE_ROOT =
  process.env.EQMD_VERIFY_EVIDENCE_ROOT || '/tmp/eqmd-verify';
export const EVIDENCE_DIR = path.join(EVIDENCE_ROOT, RUN_ID);

export const PASSWORD = process.env.EQMD_VERIFY_PASSWORD || 'Verify!2026#eqmd';
export const STUDENT_EMAIL =
  process.env.EQMD_VERIFY_STUDENT_EMAIL || 'verify.student@eqmd-verify.invalid';
export const DOCTOR_EMAIL =
  process.env.EQMD_VERIFY_DOCTOR_EMAIL || 'verify.doctor@eqmd-verify.invalid';
export const PATIENT_PREFIX = 'VERIFICACAO Skill';
// The scaffold patient of this run. scaffold.py and cleanup.py derive the same
// default; both helpers pass this value so setup and cleanup cannot disagree.
export const PATIENT_NAME =
  process.env.EQMD_VERIFY_PATIENT_NAME || `${PATIENT_PREFIX} ${RUN_ID}`;
// Ownership certificate of that patient: the exact row id scaffold.py created
// and the account that created it. setup.mjs records both in scaffold.json and
// cleanup.mjs hands them to cleanup.py, which deletes by id, never by name. The
// env vars let a recovery run name the id explicitly when scaffold.json is gone.
export const PATIENT_ID = process.env.EQMD_VERIFY_PATIENT_ID || '';
export const PATIENT_CREATED_BY = process.env.EQMD_VERIFY_PATIENT_CREATED_BY || '';

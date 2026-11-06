// Cleanup: delete only the patient this run scaffolded; never touches evidence.
import fs from 'node:fs';
import path from 'node:path';

import {
  EVIDENCE_DIR,
  PATIENT_CREATED_BY,
  PATIENT_ID,
  PATIENT_NAME,
  PASSWORD,
  RUN_ID,
} from './lib/config.mjs';
import { runPythonScript } from './lib/docker.mjs';
import { ensureEvidence, readJson, writeJson } from './lib/evidence.mjs';

// The ownership certificate setup.mjs recorded for this run. Cleanup deletes by
// that id, never by name, so an equal-named row the run did not create is safe.
function recordedPatient() {
  try {
    return readJson('scaffold.json').patient || {};
  } catch {
    return {};
  }
}

const recorded = recordedPatient();
// An explicit EQMD_VERIFY_PATIENT_ID wins over the certificate: that is how a
// recovery run names a row whose scaffold.json is gone.
const patientId = PATIENT_ID || recorded.id || '';
const patientCreatedBy = PATIENT_CREATED_BY || recorded.created_by || '';

const { result, value: cleanup } = runPythonScript('cleanup.py', {
  marker: 'EQMD_VERIFY_CLEANUP',
  // A refusal is a real outcome with a payload; read it instead of throwing.
  allowNonZero: true,
  env: {
    EQMD_VERIFY_RUN_ID: RUN_ID,
    EQMD_VERIFY_PATIENT_NAME: PATIENT_NAME,
    EQMD_VERIFY_PATIENT_ID: patientId,
    EQMD_VERIFY_PATIENT_CREATED_BY: patientCreatedBy,
    EQMD_VERIFY_PASSWORD: PASSWORD,
  },
  helper: 'cleanup/rows',
});

const usersLeftActive = cleanup.users_deactivated.filter((user) => user.is_active);
const passwordsStillValid = cleanup.users_deactivated.filter((user) => user.password_still_valid);
const ok =
  result.status === 0 &&
  cleanup.refused !== true &&
  cleanup.run_patient_remaining === 0 &&
  usersLeftActive.length === 0 &&
  passwordsStillValid.length === 0;

ensureEvidence();
writeJson('cleanup.json', { ...cleanup, ok });
writeJson('cleanup-evidence-check.json', {
  evidenceDir: EVIDENCE_DIR,
  existsAfterCleanup: fs.existsSync(EVIDENCE_DIR),
  commandLogExists: fs.existsSync(path.join(EVIDENCE_DIR, 'command-log.jsonl')),
});

process.stdout.write(
  `cleanup: patient="${cleanup.patient_name}" patient_id=${cleanup.patient_id || '(none)'} ` +
    `ownership=${cleanup.ownership} patients_deleted=${cleanup.patients_deleted} ` +
    `events_deleted=${cleanup.events_deleted} users_deactivated=${cleanup.users_deactivated.length} ` +
    `run_patients_remaining=${cleanup.run_patient_remaining}` +
    `${cleanup.already_clean ? ' (already clean)' : ''}\n` +
    `cleanup left ${cleanup.verify_patients_outside_scope} VERIFICACAO patient(s) from other run ids untouched\n` +
    `cleanup removed nothing from evidence: ${EVIDENCE_DIR} still present=${fs.existsSync(EVIDENCE_DIR)}\n`,
);

if (!ok) {
  if (cleanup.refused === true) {
    process.stderr.write(`cleanup REFUSED: ${cleanup.reason}\n`);
  } else {
    process.stderr.write('cleanup verification FAILED\n');
  }
  process.exitCode = 1;
}

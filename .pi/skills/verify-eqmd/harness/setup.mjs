// Create the disposable users/patient the journeys drive, and record the manifest.
import fs from 'node:fs';
import path from 'node:path';

import { HARNESS_DIR, PASSWORD, PATIENT_NAME, RUN_ID } from './lib/config.mjs';
import { runPythonScript } from './lib/docker.mjs';
import { ensureEvidence, writeJson } from './lib/evidence.mjs';

const playwrightPackage = path.join(HARNESS_DIR, 'node_modules', 'playwright', 'package.json');
if (!fs.existsSync(playwrightPackage)) {
  process.stderr.write(`playwright is not installed; run: cd ${HARNESS_DIR} && npm install\n`);
  process.exit(1);
}
const playwrightVersion = JSON.parse(fs.readFileSync(playwrightPackage, 'utf8')).version;

const { value: scaffold } = runPythonScript('scaffold.py', {
  marker: 'EQMD_VERIFY_SCAFFOLD',
  env: {
    EQMD_VERIFY_RUN_ID: RUN_ID,
    EQMD_VERIFY_PATIENT_NAME: PATIENT_NAME,
    EQMD_VERIFY_PASSWORD: PASSWORD,
  },
  helper: 'setup/scaffold',
});

// scaffold.py refuses to reuse a patient, so the id/creator/timestamp it reports
// describe a row this invocation created. Without all three, cleanup could not
// prove ownership and must not delete anything.
const certificate = scaffold.patient || {};
if (!certificate.id || !certificate.name || !certificate.created_by || !certificate.created_at) {
  throw new Error(
    `scaffold.py did not report the patient ownership certificate ` +
      `(id/name/created_by/created_at) for "${PATIENT_NAME}"; cleanup could not ` +
      `prove which row belongs to run ${RUN_ID}`,
  );
}

ensureEvidence();
writeJson('scaffold.json', { ...scaffold, playwrightVersion });
process.stdout.write(
  `scaffolded patient ${certificate.name} (${certificate.id}) ` +
    `created_by=${certificate.created_by} created_at=${certificate.created_at}\n` +
    `  student ${scaffold.student.email} add_event=${scaffold.student.can_add_event}\n` +
    `  doctor  ${scaffold.doctor.email} change_event=${scaffold.doctor.can_change_event}\n` +
    `  playwright ${playwrightVersion} (system Chrome channel, no download)\n` +
    `evidence: ${process.env.EQMD_VERIFY_EVIDENCE_ROOT || '/tmp/eqmd-verify'}/${RUN_ID}\n`,
);

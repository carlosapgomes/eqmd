// Read-only database evidence for one moment of a journey.
import { RUN_ID } from './config.mjs';
import { runPythonScript } from './docker.mjs';
import { writeJson } from './evidence.mjs';

export function probePatient(label, patientId, { filePath = '' } = {}) {
  const { value } = runPythonScript('probe.py', {
    marker: 'EQMD_VERIFY_PROBE',
    env: {
      EQMD_VERIFY_RUN_ID: RUN_ID,
      EQMD_VERIFY_PROBE_PATIENT: patientId,
      EQMD_VERIFY_PROBE_FILE: filePath,
    },
    helper: `probe/${label}`,
  });
  writeJson(`db/${label}.json`, value);
  return value;
}

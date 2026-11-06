// Orchestrator: doctor -> setup -> journey(s) -> cleanup, evidence kept per run.
// Usage: npm run verify -- --journeys j3      (comma-separated: j1,j2,...)
import { spawnSync } from 'node:child_process';
import path from 'node:path';

import { HARNESS_DIR, RUN_ID } from './lib/config.mjs';
import { ensureEvidence, writeJson } from './lib/evidence.mjs';

const JOURNEYS = {
  j1: 'journey-j1-draft-create.mjs',
  j2: 'journey-j2-drafts-only.mjs',
  j3: 'journey-j3-finalize.mjs',
  j4: 'journey-j4-discharge.mjs',
  j5: 'journey-j5-photo-draft.mjs',
  j6: 'journey-j6-apac-update.mjs',
};

function parseArgs(argv) {
  const options = { journeys: ['j3'], skipDoctor: false };
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === '--journeys') {
      options.journeys = String(argv[++index] || '')
        .split(',')
        .map((value) => value.trim())
        .filter(Boolean);
    } else if (arg === '--all') {
      options.journeys = Object.keys(JOURNEYS);
    } else if (arg === '--skip-doctor') {
      options.skipDoctor = true;
    } else {
      throw new Error(`unknown argument: ${arg}`);
    }
  }
  for (const journey of options.journeys) {
    if (!JOURNEYS[journey]) {
      throw new Error(`unknown journey "${journey}"; known: ${Object.keys(JOURNEYS).join(', ')}`);
    }
  }
  return options;
}

function run(script) {
  const started = Date.now();
  const result = spawnSync(process.execPath, [path.join(HARNESS_DIR, script)], {
    stdio: 'inherit',
    env: {
      ...process.env,
      EQMD_VERIFY_RUN_ID: RUN_ID,
      // Ownership always comes from this run's own scaffold.json. Blank the
      // inherited ids so a leftover export cannot point cleanup at another
      // run's patient (cleanup refuses on mismatch, but never gets that far).
      EQMD_VERIFY_PATIENT_ID: '',
      EQMD_VERIFY_PATIENT_CREATED_BY: '',
    },
  });
  return { script, exitCode: result.status ?? 1, durationMs: Date.now() - started };
}

const options = parseArgs(process.argv.slice(2));
ensureEvidence();
const summary = { runId: RUN_ID, startedAt: new Date().toISOString(), steps: [], status: 'passed' };

function record(step) {
  summary.steps.push(step);
  if (step.exitCode !== 0) summary.status = 'failed';
  return step;
}

if (!options.skipDoctor) {
  record(run('doctor.mjs'));
}
if (summary.status === 'passed') {
  for (const journey of options.journeys) {
    // Fresh scaffold rows per journey so counts on the timeline stay exact.
    record(run('setup.mjs'));
    // setup.mjs refuses to adopt a patient it did not create. When it refuses,
    // nothing was scaffolded, so do not drive a journey against the previous
    // (or another run's) rows; the final cleanup below still runs.
    if (summary.status !== 'passed') break;
    record(run(JOURNEYS[journey]));
    try {
      record(run('cleanup.mjs'));
    } catch (error) {
      summary.steps.push({ script: 'cleanup.mjs', exitCode: 1, error: error.message });
      summary.status = 'failed';
    }
  }
}
// Final sweep under the same run id: cleanup.py deletes by this run's recorded
// patient id only, so this repeats the same single-patient deletion (a no-op
// when the per-journey cleanup already ran) and clears rows this run left when
// that cleanup failed. It never touches another run's patient.
record(run('cleanup.mjs'));

summary.finishedAt = new Date().toISOString();
writeJson('summary.json', summary);
process.stdout.write(`\nrun ${summary.status}: ${summary.steps.length} helper invocations, evidence in /tmp/eqmd-verify/${RUN_ID}\n`);
if (summary.status !== 'passed') {
  process.exitCode = 1;
}

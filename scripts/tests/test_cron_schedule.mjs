import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..');
const cronPath = path.join(repoRoot, 'deploy/eon/cron/eqmd.cron.example');
const runbookPath = path.join(
  repoRoot,
  'deploy/eon/cron/install-and-reverse.md',
);
const JOB_PREFIX = '# EQMD_JOB ';

const EXPECTED = new Map([
  ['*/5 * * * *', 'update_dashboard_stats'],
  ['2-59/5 * * * *', 'update_ward_mapping_cache'],
  ['0 6 * * *', 'check_user_expiration'],
  ['0 8 * * *', 'send_expiration_notifications'],
  ['0 7 * * 0', 'lifecycle_report'],
]);

function read(file) {
  return readFileSync(file, 'utf8');
}

function jobLines(raw) {
  return raw
    .split(/\r?\n/)
    .filter((line) => line.startsWith(JOB_PREFIX))
    .map((line) => line.slice(JOB_PREFIX.length));
}

test('the file is installed suspended with exactly five marked jobs', () => {
  const raw = read(cronPath);
  const active = raw
    .split(/\r?\n/)
    .filter((line) => /^[0-9*]/.test(line));
  assert.deepEqual(active, [], 'no job may be active before E14');
  assert.equal(jobLines(raw).length, 5);
  assert.ok(
    raw.includes('--env-file <EQMD_APP_DIR>/env.eon'),
    'cron job lines must pass --env-file to compose',
  );
});

test('the five LOCAL schedules and commands are exact', () => {
  const jobs = jobLines(read(cronPath));
  assert.equal(jobs.length, 5);
  const parsed = new Map();
  for (const job of jobs) {
    const match = job.match(
      /^(\S+ \S+ \S+ \S+ \S+) root flock -n \/run\/lock\/eqmd-[a-z0-9-]+\.lock docker compose -f <EQMD_APP_DIR>\/docker-compose\.eon\.yml --env-file <EQMD_APP_DIR>\/env\.eon exec -T eqmd python manage\.py ([a-z_]+)$/,
    );
    assert.ok(match, `unexpected job line: ${job}`);
    parsed.set(match[1], match[2]);
  }
  assert.deepEqual(parsed, EXPECTED);
});

test('every job uses flock -n, exec -T and the absolute compose path', () => {
  for (const job of jobLines(read(cronPath))) {
    assert.match(job, /flock -n \/run\/lock\/eqmd-[a-z0-9-]+\.lock/);
    assert.match(job, /docker compose -f <EQMD_APP_DIR>\/docker-compose\.eon\.yml/);
    assert.match(job, / exec -T eqmd python manage\.py /);
  }
});

test('no Firebase or sync command is scheduled', () => {
  const raw = read(cronPath).toLowerCase();
  assert.doesNotMatch(raw, /firebase|sync_firebase_data/);
});

test('SHELL and PATH are declared and the file ends with one newline', () => {
  const raw = read(cronPath);
  assert.match(raw, /^SHELL=\/bin\/bash$/m);
  assert.match(
    raw,
    /^PATH=\/usr\/local\/sbin:\/usr\/local\/bin:\/usr\/sbin:\/usr\/bin:\/sbin:\/bin$/m,
  );
  assert.ok(raw.endsWith('\n'));
  assert.ok(!raw.endsWith('\n\n'));
});

test('comments document the America/Bahia local-time assumption', () => {
  const raw = readFileSync(cronPath, 'utf8');
  assert.match(raw, /America\/Bahia/);
  assert.match(raw, /timedatectl/);
  assert.match(raw, /origin value, unchanged/);
});

test('runbook covers TZ preflight, E14 and both rollback regimes', () => {
  const runbook = read(runbookPath);
  assert.match(runbook, /timedatectl/i);
  assert.match(runbook, /America\/Bahia/);
  assert.match(runbook, /# EQMD_JOB/);
  assert.match(runbook, /E14/);
  assert.match(runbook, /rollback|revers[aã]o/i);
  assert.match(runbook, /crontab/i);
});

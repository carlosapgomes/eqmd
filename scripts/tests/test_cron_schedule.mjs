import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..');
const cronPath = path.join(repoRoot, 'deploy/eon/cron/eqmd.cron');
const runbookPath = path.join(
  repoRoot,
  'deploy/eon/cron/install-and-reverse.md',
);
const JOB_PREFIX = '# EQMD_JOB ';

const EXPECTED = new Map([
  ['*/5 * * * *', 'update_dashboard_stats'],
  ['2-59/5 * * * *', 'update_ward_mapping_cache'],
  ['0 9 * * *', 'check_user_expiration'],
  ['0 11 * * *', 'send_expiration_notifications'],
  ['0 10 * * 0', 'lifecycle_report'],
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
});

test('the five UTC schedules and commands are exact', () => {
  const jobs = jobLines(read(cronPath));
  assert.equal(jobs.length, 5);
  const parsed = new Map();
  for (const job of jobs) {
    const match = job.match(
      /^(\S+ \S+ \S+ \S+ \S+) root flock -n \/run\/lock\/eqmd-[a-z0-9-]+\.lock docker compose -f \/srv\/apps\/eqmd\/docker-compose\.eon\.yml exec -T eqmd python manage\.py ([a-z_]+)$/,
    );
    assert.ok(match, `unexpected job line: ${job}`);
    parsed.set(match[1], match[2]);
  }
  assert.deepEqual(parsed, EXPECTED);
});

test('every job uses flock -n, exec -T and the absolute compose path', () => {
  for (const job of jobLines(read(cronPath))) {
    assert.match(job, /flock -n \/run\/lock\/eqmd-[a-z0-9-]+\.lock/);
    assert.match(job, /docker compose -f \/srv\/apps\/eqmd\/docker-compose\.eon\.yml/);
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

test('comments document every Bahia to UTC pair', () => {
  const raw = read(cronPath);
  assert.match(raw, /Bahia: \*\/5 \* \* \* \* -> UTC: \*\/5 \* \* \* \*/);
  assert.match(
    raw,
    /Bahia: 2-59\/5 \* \* \* \* -> UTC: 2-59\/5 \* \* \* \*/,
  );
  assert.match(raw, /Bahia: 0 6 \* \* \* -> UTC: 0 9 \* \* \*/);
  assert.match(raw, /Bahia: 0 8 \* \* \* -> UTC: 0 11 \* \* \*/);
  assert.match(raw, /Bahia: 0 7 \* \* 0 -> UTC: 0 10 \* \* 0/);
});

test('runbook covers UTC preflight, E14 and both rollback regimes', () => {
  const runbook = read(runbookPath);
  assert.match(runbook, /timedatectl/i);
  assert.match(runbook, /UTC/);
  assert.match(runbook, /# EQMD_JOB/);
  assert.match(runbook, /E14/);
  assert.match(runbook, /rollback|revers[aã]o/i);
  assert.match(runbook, /crontab/i);
});

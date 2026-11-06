// Doctor: read-only "is this stack worth driving?" check. Never starts a server.
import fs from 'node:fs';
import path from 'node:path';

import { BASE_URL, CONTAINER, REPO_ROOT, RUN_ID, STUDENT_EMAIL } from './lib/config.mjs';
import { dockerCli, dockerExec } from './lib/docker.mjs';
import { ensureEvidence, writeJson } from './lib/evidence.mjs';

const checks = [];
let ready = true;

function record(name, ok, detail) {
  checks.push({ name, ok, detail });
  if (!ok) ready = false;
  const status = ok ? 'ok  ' : 'FAIL';
  process.stdout.write(`[${status}] ${name}: ${detail}\n`);
}

// 1. The container that owns the dev server is already running.
const state = dockerCli(['inspect', '-f', '{{.State.Status}}', CONTAINER], {
  helper: 'doctor/container-state',
  note: 'read-only container status; never starts/stops anything',
});
const containerUp = state.status === 0 && state.stdout.trim() === 'running';
record('container running', containerUp, `${CONTAINER} state=${state.stdout.trim() || '?'}`);

// 2. The mapped port answers and the login page is the expected app.
try {
  const response = await fetch(`${BASE_URL}/accounts/login/`);
  const html = await response.text();
  const titleOk = /<title>Login - EquipeMed<\/title>/.test(html);
  record(
    'login page reachable',
    response.status === 200 && titleOk,
    `GET ${BASE_URL}/accounts/login/ -> ${response.status}, title ok=${titleOk}`,
  );
  const csrf = /name="csrfmiddlewaretoken" value="([^"]+)"/.exec(html);
  record(
    'login form carries a CSRF token',
    Boolean(csrf),
    csrf ? 'csrfmiddlewaretoken present (session-less GET still issues it)' : 'no token in form',
  );
} catch (error) {
  record('login page reachable', false, `${BASE_URL} unreachable: ${error.message}`);
}

// 3. The auth path is guarded: send the login form with no token and no cookies.
// CsrfViewMiddleware rejects it before the login view runs, so this proves the
// gate exists without creating a session or writing a row. Credential validity
// is NOT claimed here; the journeys log in through the real form.
try {
  const post = await fetch(`${BASE_URL}/accounts/login/`, {
    method: 'POST',
    headers: { 'content-type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({
      login: STUDENT_EMAIL,
      password: 'csrf-probe-not-the-password',
    }).toString(),
    redirect: 'manual',
  });
  const postBody = await post.text();
  const setCookie = post.headers.getSetCookie().join(' ');
  const sessionIssued = setCookie.includes('sessionid=');
  record(
    'login POST without a CSRF token is rejected',
    post.status === 403 && !sessionIssued,
    `POST ${BASE_URL}/accounts/login/ (no token, no cookies) -> ${post.status}, ` +
      `session cookie issued=${sessionIssued}, csrf rejection page=${/CSRF/i.test(postBody)}`,
  );
} catch (error) {
  record('login POST without a CSRF token is rejected', false, `POST failed: ${error.message}`);
}

// 4. Which checkout the running server actually serves. The dev container
// mounts its own checkout, so it can differ from this worktree.
const head = dockerExec(['bash', '-lc', 'cd /app && git rev-parse --abbrev-ref HEAD && git rev-parse --short HEAD'], {
  helper: 'doctor/served-checkout',
});
const [servedBranch, servedHead] = head.stdout.trim().split('\n');
record(
  'served checkout identified',
  Boolean(servedBranch && servedHead),
  `container /app is ${servedBranch}@${servedHead}`,
);

let worktreeHead = '';
try {
  const gitHead = fs.readFileSync(path.join(REPO_ROOT, '.git'), 'utf8').trim();
  if (gitHead.startsWith('gitdir:')) {
    const gitDir = path.resolve(REPO_ROOT, gitHead.replace('gitdir:', '').trim());
    worktreeHead = fs.readFileSync(path.join(gitDir, 'HEAD'), 'utf8').trim();
  }
} catch {
  worktreeHead = '';
}
checks.push({
  name: 'worktree HEAD (informational)',
  ok: true,
  detail: worktreeHead ? `${REPO_ROOT} -> ${worktreeHead}` : 'unreadable (linked worktree)',
});

// 5. The served code must contain the draft-supervision surface the journeys prove.
const marker = dockerExec(
  ['grep', '-c', 'Rascunho · há', '/app/apps/events/templates/events/partials/event_card_base.html'],
  { helper: 'doctor/draft-surface' },
);
const markerCount = Number.parseInt(marker.stdout.trim(), 10) || 0;
record(
  'served code has the draft review surface',
  markerCount > 0,
  `event_card_base.html draft badge matches=${markerCount}`,
);

// 6. Database reachable, read-only (no migrate, no writes).
const dbCheck = dockerExec(
  ['python', 'manage.py', 'shell', '-c', 'from django.db import connection; connection.ensure_connection(); print("DB_OK")'],
  { helper: 'doctor/db' },
);
record(
  'database reachable',
  dbCheck.status === 0 && dbCheck.stdout.includes('DB_OK'),
  dbCheck.status === 0 ? 'connection.ensure_connection() ok' : dbCheck.stderr.slice(0, 200),
);

// 7. No pending migrations. The doctor never applies them (shared dev database).
const migrateCheck = dockerExec(['python', 'manage.py', 'migrate', '--check'], {
  helper: 'doctor/migrations',
});
record(
  'no unapplied migrations',
  migrateCheck.status === 0,
  migrateCheck.status === 0
    ? 'migrate --check clean (nothing applied by this run)'
    : `unapplied migrations: ${(migrateCheck.stderr || migrateCheck.stdout).slice(0, 300)}`,
);

ensureEvidence();
writeJson('doctor.json', { runId: RUN_ID, baseUrl: BASE_URL, container: CONTAINER, ready, checks });

process.stdout.write(`\ndoctor: ${ready ? 'READY' : 'NOT READY'} (no start/stop/restart performed)\n`);
if (!ready) {
  process.exitCode = 1;
}

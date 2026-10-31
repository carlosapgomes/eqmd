#!/usr/bin/env node
/**
 * Disposable rehearsal for slice s5 cron mechanics.
 *
 * Proves (a) flock -n rejects a concurrent second run observably and
 * releases after the holder exits, and (b) the cron command pattern
 * `docker compose -f X exec -T svc cmd` works against a minimal
 * disposable compose. Real per-minute firing and single-source proof
 * are explicitly deferred to the s7 e2e.
 *
 * Every docker resource uses eqmd_s5_* exact names. The script aborts
 * if an expected name already exists and removes only names it created.
 */
import { spawn, spawnSync } from 'node:child_process';
import { mkdirSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..');
const evidenceDir = path.join(repoRoot, 'temp/migracao-eon', 's5');

const ALPINE_IMAGE =
  'alpine@sha256:' +
  '28bd5fe8b56d1bd048e5babf5b10710ebe0bae67db86916198a6eec434943f8b';
const PREFIX = 'eqmd_s5_';
const suffix =
  process.env.EQMD_S5_RUN_SUFFIX || `${process.pid}-${Date.now()}`;
const projectName = `${PREFIX}proj_${suffix}`;
const networkName = `${PREFIX}net_${suffix}`;
const containerName = `${PREFIX}sleeper_${suffix}`;
const scratch = path.join('/tmp/opencode', `${PREFIX}${suffix}`);
const composeFile = path.join(scratch, 'compose.yml');
const lockFile = path.join(scratch, 'eqmd.lock');

const expected = {
  containers: [containerName],
  networks: [networkName],
};
const created = { containers: [], networks: [] };

const COMPOSE = `name: ${projectName}
services:
  sleeper:
    image: ${ALPINE_IMAGE}
    container_name: ${containerName}
    command: ["sh", "-c", "sleep 300"]
    networks:
      - ${networkName}
networks:
  ${networkName}:
    external: true
`;

function docker(args, options = {}) {
  const result = spawnSync('docker', args, {
    encoding: options.encoding === null ? null : 'utf8',
    input: options.input,
    maxBuffer: 16 * 1024 * 1024,
  });
  if (result.error) {
    throw new Error(`docker ${args[0]} failed to spawn: ${result.error.message}`);
  }
  const stderr = result.stderr ? result.stderr.toString() : '';
  if (result.status !== 0 && !options.allowFailure) {
    const stdout = result.stdout ? result.stdout.toString() : '';
    throw new Error(
      `docker ${args.join(' ')} exited ${result.status}\n${stderr}${stdout}`,
    );
  }
  return result;
}

function resourceExists(kind, name) {
  const args =
    kind === 'containers'
      ? ['inspect', '--type', 'container', name]
      : ['network', 'inspect', name];
  return docker(args, { allowFailure: true }).status === 0;
}

function assertNamesFree() {
  const conflicts = [];
  for (const [kind, names] of Object.entries(expected)) {
    for (const name of names) {
      if (resourceExists(kind, name)) conflicts.push(`${kind}: ${name}`);
    }
  }
  if (conflicts.length > 0) {
    throw new Error(
      'refusing to run: expected disposable names already exist ' +
        `(${conflicts.join(', ')}). Remove them manually only if stale; ` +
        'this script never deletes resources it did not create.',
    );
  }
}

function remainingResources() {
  const residue = { containers: [], networks: [] };
  for (const [kind, names] of Object.entries(expected)) {
    for (const name of names) {
      if (resourceExists(kind, name)) residue[kind].push(name);
    }
  }
  return residue;
}

function cleanup() {
  for (const name of created.containers) {
    docker(['rm', '-f', name], { allowFailure: true });
  }
  for (const name of created.networks) {
    docker(['network', 'rm', name], { allowFailure: true });
  }
  try {
    rmSync(scratch, { recursive: true, force: true });
  } catch (error) {
    console.error(`[s5] scratch cleanup warning: ${error.message}`);
  }
}

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    cleanup();
    process.exit(130);
  });
}

function check(condition, message) {
  if (!condition) throw new Error(message);
}

async function waitUntil(predicate, message, timeoutMs = 10000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (predicate()) return;
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  throw new Error(message);
}

async function proveFlock() {
  const holder = spawn('flock', [
    '-n',
    lockFile,
    'sh',
    '-c',
    'echo LOCK_HELD; sleep 3',
  ]);
  let holderOutput = '';
  holder.stdout.on('data', (data) => {
    holderOutput += data.toString();
  });
  await waitUntil(
    () => holderOutput.includes('LOCK_HELD'),
    'first flock holder did not start',
  );

  const second = spawnSync('flock', [
    '-n',
    lockFile,
    'sh',
    '-c',
    'echo SECOND_ACQUIRED',
  ], { encoding: 'utf8' });
  check(second.status !== 0, 'second flock unexpectedly acquired the lock');
  check(
    !second.stdout.includes('SECOND_ACQUIRED'),
    'second run executed while the lock was held',
  );

  const holderCode = await new Promise((resolve) => {
    holder.on('exit', (code) => resolve(code));
  });
  check(holderCode === 0, `first flock holder exited ${holderCode}`);

  const third = spawnSync('flock', [
    '-n',
    lockFile,
    'sh',
    '-c',
    'echo THIRD_ACQUIRED',
  ], { encoding: 'utf8' });
  check(third.status === 0, 'lock was not released after holder exit');
  check(third.stdout.includes('THIRD_ACQUIRED'), 'third run did not execute');

  return {
    first: holderOutput.trim(),
    first_exit: holderCode,
    second_exit: second.status,
    second_stdout: second.stdout.trim(),
    third_exit: third.status,
    third_stdout: third.stdout.trim(),
  };
}

async function rehearse(evidence) {
  mkdirSync(scratch, { recursive: true });
  assertNamesFree();
  console.log('[s5] exact-name check passed; creating disposables');

  docker(['network', 'create', networkName]);
  created.networks.push(networkName);

  writeFileSync(composeFile, COMPOSE);
  docker([
    'compose', '-f', composeFile, '-p', projectName, 'up', '-d',
  ]);
  created.containers.push(containerName);

  await waitUntil(
    () =>
      docker(
        ['inspect', '-f', '{{.State.Running}}', containerName],
        { allowFailure: true },
      ).stdout.trim() === 'true',
    'disposable compose container did not start',
  );

  const composeExec = docker([
    'compose', '-f', composeFile, '-p', projectName,
    'exec', '-T', 'sleeper', 'sh', '-c', 'echo COMPOSE_EXEC_OK',
  ]);
  check(
    composeExec.stdout.includes('COMPOSE_EXEC_OK'),
    'compose exec -T did not reach the service',
  );

  const flockProof = await proveFlock();
  check(flockProof.second_exit !== 0, 'flock concurrency proof failed');

  evidence.compose_exec = {
    exit: composeExec.status,
    stdout: composeExec.stdout.trim(),
  };
  evidence.flock = flockProof;
  evidence.limits = [
    'real per-minute cron firing deferred to s7 e2e',
    'single-source (origin vs destination) proof deferred to s7 e2e',
  ];

  console.log(`[s5] compose exec -T output=${composeExec.stdout.trim()}`);
  console.log(
    `[s5] flock: holder=${flockProof.first_exit} ` +
      `second=${flockProof.second_exit} third=${flockProof.third_exit}`,
  );
  console.log('[s5] real per-minute firing and single-source proof: s7 e2e');
}

async function main() {
  mkdirSync(evidenceDir, { recursive: true });
  const evidence = { alpine_image: ALPINE_IMAGE, prefix: PREFIX };
  let failure = null;
  try {
    await rehearse(evidence);
  } catch (error) {
    failure = error;
    console.error(`[s5] FAIL: ${error.message}`);
  } finally {
    cleanup();
  }

  const residue = remainingResources();
  evidence.cleanup_residue = residue;
  console.log(`[s5] cleanup residue: ${JSON.stringify(residue)}`);
  try {
    writeFileSync(
      path.join(evidenceDir, 'rehearsal-metrics.json'),
      `${JSON.stringify(evidence, null, 2)}\n`,
    );
  } catch (error) {
    console.error(`[s5] could not write metrics: ${error.message}`);
  }

  const hasResidue = residue.containers.length + residue.networks.length > 0;
  if (hasResidue) {
    failure = failure ?? new Error('expected eqmd_s5_* names remain');
  }
  if (failure) {
    process.exitCode = 1;
    return;
  }
  console.log('[s5] PASS');
}

main().catch((error) => {
  console.error(`[s5] FAIL: ${error.message}`);
  cleanup();
  process.exitCode = 1;
});

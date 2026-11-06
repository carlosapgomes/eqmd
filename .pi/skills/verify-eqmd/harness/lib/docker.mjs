// Thin wrapper over `docker exec` so every DB touch is logged and scoped.
// The skill never starts or stops containers: this module can only exec.
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

import { CONTAINER, HARNESS_DIR } from './config.mjs';
import { logCommand } from './evidence.mjs';

export function dockerExec(args, { input, env = {}, helper = 'docker', note = '' } = {}) {
  const flagArgs = Object.entries(env).flatMap(([key, value]) => ['-e', `${key}=${value}`]);
  const argv = ['exec', '-i', ...flagArgs, CONTAINER, ...args];
  return runDocker(argv, { input, helper, note });
}

/** Docker CLI call that is NOT `docker exec` (inspect, ps, ...). */
export function dockerCli(args, { helper = 'docker', note = '' } = {}) {
  return runDocker(args, { input: undefined, helper, note });
}

function runDocker(argv, { input, helper, note }) {
  const started = Date.now();
  const result = spawnSync('docker', argv, {
    input,
    encoding: 'utf8',
    maxBuffer: 32 * 1024 * 1024,
  });
  const durationMs = Date.now() - started;
  const stdout = result.stdout || '';
  logCommand({
    helper,
    argv,
    exitCode: result.status ?? 1,
    durationMs,
    note,
    stdoutTail: `${stdout}${result.stderr || ''}`,
  });
  return { status: result.status ?? 1, stdout, stderr: result.stderr || '', argv };
}

/**
 * Execute one python script from harness/ inside the dev container through
 * `manage.py shell` (stdin is executed as code, Django already configured).
 * Returns the parsed marker line the script prints.
 *
 * `allowNonZero` returns the exit status instead of throwing, for helpers that
 * refuse on purpose after printing their payload (cleanup.py). A helper that
 * dies without printing the marker still throws.
 */
export function runPythonScript(
  scriptName,
  { env = {}, marker, helper, allowNonZero = false } = {},
) {
  const scriptPath = path.join(HARNESS_DIR, scriptName);
  const source = fs.readFileSync(scriptPath, 'utf8');
  const result = dockerExec(['python', 'manage.py', 'shell'], {
    input: source,
    env,
    helper: helper || scriptName,
    note: `manage.py shell < ${scriptName}`,
  });
  if (result.status !== 0 && !allowNonZero) {
    throw new Error(
      `${scriptName} failed (exit ${result.status}):\n${result.stderr || result.stdout}`,
    );
  }
  if (!marker) {
    return { result };
  }
  const line = result.stdout
    .split('\n')
    .find((candidate) => candidate.startsWith(`${marker}=`));
  if (!line) {
    throw new Error(
      `${scriptName} did not print ${marker} (exit ${result.status}):\n` +
        `${result.stdout}${result.stderr}`,
    );
  }
  return { result, value: JSON.parse(line.slice(marker.length + 1)) };
}

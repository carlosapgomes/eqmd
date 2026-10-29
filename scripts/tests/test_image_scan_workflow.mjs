import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, readFileSync, writeFileSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..');
const workflowPath = path.join(
  repoRoot,
  '.github',
  'workflows',
  'build-and-push.yml',
);
const helperRel = path.join('scripts', 'validate-image-scan-sarif.mjs');
const helperPath = path.join(repoRoot, helperRel);

const scratch = mkdtempSync(path.join(os.tmpdir(), 'sarif-gate-'));

function sarifDoc(results) {
  return {
    version: '2.1.0',
    $schema: 'https://json.schemastore.org/sarif-2.1.0.json',
    runs: [
      {
        tool: { driver: { name: 'Grype', version: 'v0.118.0' } },
        results,
      },
    ],
  };
}

function finding() {
  return {
    ruleId: 'CVE-2026-0001',
    level: 'error',
    message: { text: 'synthetic finding for regression gate' },
  };
}

function fixture(name, content) {
  const target = path.join(scratch, name);
  writeFileSync(target, content);
  return target;
}

const validWithFindings = fixture(
  'valid-findings.sarif',
  JSON.stringify(sarifDoc([finding()])),
);
const validZeroFindings = fixture(
  'valid-empty.sarif',
  JSON.stringify(sarifDoc([])),
);
const emptyFile = fixture('empty.sarif', '');
const truncatedFile = fixture(
  'truncated.sarif',
  '{"version": "2.1.0", "runs": [',
);
const invalidJson = fixture('invalid.sarif', 'not json{{{');
const notSarif = fixture('not-sarif.json', JSON.stringify({ foo: 1 }));
const missingFile = path.join(scratch, 'never-written.sarif');
const wrongVersionNullRun = fixture(
  'wrong-version-null-run.sarif',
  JSON.stringify({ version: 'not-sarif', runs: [null] }),
);
const missingToolMalformedResults = fixture(
  'missing-tool-malformed-results.sarif',
  JSON.stringify({ version: '2.1.0', runs: [{ results: 'invalid' }] }),
);
const runsNotArray = fixture(
  'runs-not-array.sarif',
  JSON.stringify({ version: '2.1.0', runs: 'nope' }),
);
const runAsString = fixture(
  'run-as-string.sarif',
  JSON.stringify({ version: '2.1.0', runs: ['nope'] }),
);
const toolAsString = fixture(
  'tool-as-string.sarif',
  JSON.stringify({ version: '2.1.0', runs: [{ tool: 'Grype', results: [] }] }),
);
const driverNameEmpty = fixture(
  'driver-name-empty.sarif',
  JSON.stringify({
    version: '2.1.0',
    runs: [{ tool: { driver: { name: '' } }, results: [] }],
  }),
);
const resultsAsObject = fixture(
  'results-as-object.sarif',
  JSON.stringify({
    version: '2.1.0',
    runs: [{ tool: { driver: { name: 'Grype' } }, results: {} }],
  }),
);

function grypeLikeSarif({ results, executionSuccessful }) {
  return JSON.stringify({
    version: '2.1.0',
    runs: [
      {
        tool: {
          driver: {
            name: 'Grype',
            version: 'v0.118.0',
            informationUri: 'https://github.com/anchore/grype',
            rules: [],
          },
        },
        invocations: [{ executionSuccessful }],
        results,
      },
    ],
  });
}

const realisticZeroFindings = fixture(
  'realistic-zero.sarif',
  grypeLikeSarif({ results: [], executionSuccessful: true }),
);
const realisticWithFindings = fixture(
  'realistic-findings.sarif',
  grypeLikeSarif({ results: [finding()], executionSuccessful: true }),
);
const selfDeclaredFailure = fixture(
  'self-declared-failure.sarif',
  grypeLikeSarif({ results: [], executionSuccessful: false }),
);

function runHelper(args) {
  try {
    const stdout = execFileSync(process.execPath, [helperPath, ...args], {
      encoding: 'utf8',
    });
    return { status: 0, output: stdout };
  } catch (err) {
    return {
      status: typeof err.status === 'number' ? err.status : 1,
      output: `${err.stdout ?? ''}${err.stderr ?? ''}`,
    };
  }
}

test('helper accepts a valid SARIF report with findings', () => {
  const result = runHelper([validWithFindings]);
  assert.equal(result.status, 0, result.output);
  assert.match(result.output, /VALIDATED/);
});

test('helper accepts a valid SARIF report with zero findings', () => {
  const result = runHelper([validZeroFindings]);
  assert.equal(result.status, 0, result.output);
  assert.match(result.output, /VALIDATED/);
});

test('helper rejects a missing SARIF file', () => {
  const result = runHelper([missingFile]);
  assert.notEqual(result.status, 0);
  assert.doesNotMatch(result.output, /VALIDATED/);
});

test('helper rejects an empty SARIF file', () => {
  const result = runHelper([emptyFile]);
  assert.notEqual(result.status, 0);
  assert.doesNotMatch(result.output, /VALIDATED/);
});

test('helper rejects a truncated SARIF file', () => {
  const result = runHelper([truncatedFile]);
  assert.notEqual(result.status, 0);
  assert.doesNotMatch(result.output, /VALIDATED/);
});

test('helper rejects invalid JSON', () => {
  const result = runHelper([invalidJson]);
  assert.notEqual(result.status, 0);
  assert.doesNotMatch(result.output, /VALIDATED/);
});

test('helper rejects JSON without SARIF structure', () => {
  const result = runHelper([notSarif]);
  assert.notEqual(result.status, 0);
  assert.doesNotMatch(result.output, /VALIDATED/);
});

test('helper rejects a missing path argument', () => {
  const result = runHelper([]);
  assert.notEqual(result.status, 0);
  assert.doesNotMatch(result.output, /VALIDATED/);
});

function rejects(title, target) {
  test(title, () => {
    const result = runHelper([target]);
    assert.notEqual(result.status, 0, result.output);
    assert.doesNotMatch(result.output, /VALIDATED/);
  });
}

rejects(
  'helper rejects an unsupported version with a null run',
  wrongVersionNullRun,
);
rejects(
  'helper rejects a missing tool with malformed results',
  missingToolMalformedResults,
);
rejects('helper rejects runs that is not an array', runsNotArray);
rejects('helper rejects a run that is not an object', runAsString);
rejects('helper rejects a tool that is not an object', toolAsString);
rejects('helper rejects an empty tool name', driverNameEmpty);
rejects('helper rejects results that are not an array', resultsAsObject);
rejects(
  'helper rejects a report that declares execution failure',
  selfDeclaredFailure,
);

test('helper accepts realistic Grype SARIF with zero findings', () => {
  const result = runHelper([realisticZeroFindings]);
  assert.equal(result.status, 0, result.output);
  assert.match(result.output, /VALIDATED/);
});

test('helper accepts realistic Grype SARIF with findings', () => {
  const result = runHelper([realisticWithFindings]);
  assert.equal(result.status, 0, result.output);
  assert.match(result.output, /VALIDATED/);
});

function workflowText() {
  return readFileSync(workflowPath, 'utf8');
}

function scanTail() {
  const text = workflowText();
  const start = text.indexOf('Image vulnerability scan');
  assert.notEqual(start, -1, 'scan step not found in workflow');
  return text.slice(start);
}

test('workflow scans with a supported Anchore major version', () => {
  const text = workflowText();
  assert.match(text, /uses:\s*anchore\/scan-action@v7\b/);
  assert.doesNotMatch(text, /anchore\/scan-action@v3\b/);
});

test('workflow still scans the build digest with informative policy', () => {
  const tail = scanTail();
  assert.match(tail, /steps\.build\.outputs\.digest/);
  assert.match(tail, /fail-build:\s*false/);
  assert.match(tail, /severity-cutoff:\s*high/);
});

test('workflow validates SARIF with the same helper under test', () => {
  const tail = scanTail();
  assert.match(tail, /id:\s*validate-sarif/);
  assert.ok(
    tail.includes(`node ${helperRel}`),
    'validate step must invoke the helper exercised here',
  );
  const validateAt = tail.indexOf('id: validate-sarif');
  const invokeAt = tail.indexOf(`node ${helperRel}`, validateAt);
  const publishAt = tail.indexOf('validated-sarif=', validateAt);
  assert.ok(invokeAt !== -1 && publishAt !== -1 && invokeAt < publishAt);
});

test('workflow uploads only the validated SARIF path', () => {
  const tail = scanTail();
  const validatedRef = 'steps.validate-sarif.outputs.validated-sarif';
  assert.ok(tail.includes(`sarif_file: \${{ ${validatedRef} }}`));
  assert.ok(tail.includes(`path: \${{ ${validatedRef} }}`));
  assert.doesNotMatch(tail, /sarif_file:\s*\$\{\{\s*steps\.scan\.outputs\.sarif/);
});

test('workflow never silences step failures', () => {
  const tail = scanTail();
  assert.doesNotMatch(tail, /continue-on-error/);
});

function stepCondition(stepName) {
  const tail = scanTail();
  const nameAt = tail.indexOf(stepName);
  assert.notEqual(nameAt, -1, `${stepName} step not found`);
  const next = tail.indexOf('- name:', nameAt + stepName.length);
  const block = next === -1 ? tail.slice(nameAt) : tail.slice(nameAt, next);
  const match = block.match(/\n\s*if:\s*(.+)/);
  assert.ok(match, `${stepName} step has no if condition`);
  return match[1].trim();
}

function tokenizeCondition(source) {
  const tokens = source.match(/!=|!|&&|\|\||==|\(|\)|'[^']*'|[A-Za-z0-9_.-]+/g);
  assert.ok(tokens, `no tokens in ${source}`);
  const rebuilt = tokens.join('');
  const stripped = source.replace(/\s+/g, '');
  assert.equal(rebuilt, stripped, `unsupported syntax in ${source}`);
  return tokens;
}

function callStatus(name, ctx) {
  if (name === 'success') return !ctx.failed && !ctx.cancelled;
  if (name === 'failure') return ctx.failed && !ctx.cancelled;
  if (name === 'cancelled') return ctx.cancelled;
  if (name === 'always') return true;
  throw new Error(`unsupported status function ${name}`);
}

function resolveRef(token, ctx) {
  if (token === 'github.event_name') return ctx.eventName;
  const match = token.match(/^steps\.(.+)\.outputs\.(.+)$/);
  if (match) return ctx.outputs[match[1]]?.[match[2]] ?? '';
  throw new Error(`unsupported reference ${token}`);
}

function evaluateCondition(source, ctx) {
  const tokens = tokenizeCondition(source);
  let pos = 0;
  const peek = () => tokens[pos];
  const next = () => tokens[pos++];
  function parseOr() {
    let value = parseAnd();
    while (peek() === '||') {
      next();
      value = parseAnd() || value;
    }
    return value;
  }
  function parseAnd() {
    let value = parseUnary();
    while (peek() === '&&') {
      next();
      value = parseUnary() && value;
    }
    return value;
  }
  function parseUnary() {
    if (peek() === '!') {
      next();
      return !parseUnary();
    }
    if (peek() === '(') {
      next();
      const value = parseOr();
      assert.equal(next(), ')');
      return value;
    }
    return parsePrimary();
  }
  function parsePrimary() {
    const token = next();
    if (peek() === '(') {
      next();
      assert.equal(next(), ')', `unexpected call arguments in ${source}`);
      return callStatus(token, ctx);
    }
    if (peek() === '==' || peek() === '!=') {
      const op = next();
      const literal = next();
      assert.match(literal, /^'.*'$/, `expected string literal in ${source}`);
      const actual = resolveRef(token, ctx);
      const expected = literal.slice(1, -1);
      return op === '==' ? actual === expected : actual !== expected;
    }
    return resolveRef(token, ctx);
  }
  const value = parseOr();
  assert.equal(pos, tokens.length, `trailing tokens in ${source}`);
  return Boolean(value);
}

const SCAN_STEP = 'Image vulnerability scan';
const VALIDATE_STEP = 'Validate SARIF report';
const SECURITY_STEP = 'Upload vulnerability scan results to GitHub Security';
const ARTIFACT_STEP = 'Upload SARIF as workflow artifact';

const ORDERED_STEPS = [
  { name: SCAN_STEP, id: 'scan', outputs: { sarif: 'results.sarif' } },
  {
    name: VALIDATE_STEP,
    id: 'validate-sarif',
    outputs: { 'validated-sarif': 'results.sarif' },
  },
  { name: SECURITY_STEP, id: 'security-upload', outputs: null },
  { name: ARTIFACT_STEP, id: 'artifact-upload', outputs: null },
];

function simulate(outcomes, cancelledAt = null) {
  const ctx = { eventName: 'push', failed: false, cancelled: false, outputs: {} };
  const ran = {};
  for (const step of ORDERED_STEPS) {
    if (cancelledAt === step.name) ctx.cancelled = true;
    ran[step.name] = evaluateCondition(stepCondition(step.name), ctx);
    if (!ran[step.name]) continue;
    if ((outcomes[step.name] ?? 'success') === 'failure') {
      ctx.failed = true;
    } else if (step.outputs) {
      ctx.outputs[step.id] = step.outputs;
    }
  }
  return { ran, jobFailed: ctx.failed };
}

test('matrix: healthy scan uploads to Security and preserves the artifact', () => {
  const { ran, jobFailed } = simulate({});
  assert.deepEqual(ran, {
    [SCAN_STEP]: true,
    [VALIDATE_STEP]: true,
    [SECURITY_STEP]: true,
    [ARTIFACT_STEP]: true,
  });
  assert.equal(jobFailed, false);
});

test('matrix: scan failure skips validation and both uploads', () => {
  const { ran, jobFailed } = simulate({ [SCAN_STEP]: 'failure' });
  assert.deepEqual(ran, {
    [SCAN_STEP]: true,
    [VALIDATE_STEP]: false,
    [SECURITY_STEP]: false,
    [ARTIFACT_STEP]: false,
  });
  assert.equal(jobFailed, true);
});

test('matrix: invalid SARIF fails validation and skips both uploads', () => {
  const { ran, jobFailed } = simulate({ [VALIDATE_STEP]: 'failure' });
  assert.deepEqual(ran, {
    [SCAN_STEP]: true,
    [VALIDATE_STEP]: true,
    [SECURITY_STEP]: false,
    [ARTIFACT_STEP]: false,
  });
  assert.equal(jobFailed, true);
});

test('matrix: Security failure still preserves the valid artifact', () => {
  const { ran, jobFailed } = simulate({ [SECURITY_STEP]: 'failure' });
  assert.equal(ran[ARTIFACT_STEP], true);
  assert.equal(jobFailed, true);
});

test('matrix: cancellation skips the artifact without masking', () => {
  const { ran, jobFailed } = simulate({}, SECURITY_STEP);
  assert.equal(ran[SECURITY_STEP], false);
  assert.equal(ran[ARTIFACT_STEP], false);
  assert.equal(jobFailed, false);
});

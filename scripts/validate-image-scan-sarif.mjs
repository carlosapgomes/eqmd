#!/usr/bin/env node
// Gate a Grype-produced SARIF file before GitHub upload.
//
// Structural check only: existence, non-empty content, parseable JSON,
// supported SARIF version, well-formed runs with tool identity, and no
// self-declared execution failure. This is not a full validation of the
// SARIF schema.
import { readFileSync } from 'node:fs';

const SUPPORTED_SARIF_VERSION = '2.1.0';

const [sarifPath] = process.argv.slice(2);

function fail(message) {
  console.error(`ERROR validate-image-scan-sarif: ${message}`);
  process.exit(1);
}

function readReport(target) {
  if (!target) {
    fail('missing SARIF path argument; refusing an unknown file.');
  }
  try {
    return readFileSync(target, 'utf8');
  } catch {
    fail(`cannot read SARIF file at '${target}'.`);
  }
  return '';
}

function parseReport(raw, target) {
  if (!raw.trim()) {
    fail(`SARIF file at '${target}' is empty; refusing an empty report.`);
  }
  try {
    return JSON.parse(raw);
  } catch {
    fail(`SARIF file at '${target}' is not valid JSON.`);
  }
  return null;
}

function checkDocument(doc, target) {
  if (!doc || typeof doc !== 'object' || Array.isArray(doc)) {
    fail(`SARIF file at '${target}' is not a JSON object.`);
  }
  if (doc.version !== SUPPORTED_SARIF_VERSION) {
    fail(`SARIF file at '${target}' has unsupported version.`);
  }
  if (!Array.isArray(doc.runs) || doc.runs.length === 0) {
    fail(`SARIF file at '${target}' has no runs.`);
  }
}

function checkTool(run, index, target) {
  const tool = run.tool;
  if (!tool || typeof tool !== 'object' || Array.isArray(tool)) {
    fail(`SARIF file at '${target}' has no tool in run ${index}.`);
  }
  const driver = tool.driver;
  if (!driver || typeof driver !== 'object' || Array.isArray(driver)) {
    fail(`SARIF file at '${target}' has no tool driver in run ${index}.`);
  }
  if (typeof driver.name !== 'string' || driver.name === '') {
    fail(`SARIF file at '${target}' has no tool name in run ${index}.`);
  }
}

function checkInvocations(run, index, target) {
  if (run.invocations === undefined) return;
  if (!Array.isArray(run.invocations)) {
    fail(`SARIF file at '${target}' has malformed invocations.`);
  }
  for (const invocation of run.invocations) {
    if (!invocation || typeof invocation !== 'object') {
      fail(`SARIF file at '${target}' has malformed invocations.`);
    }
    if (invocation.executionSuccessful === false) {
      fail(`SARIF file at '${target}' declares execution failure.`);
    }
  }
}

function countResults(run, index, target) {
  if (run.results === undefined) return 0;
  if (!Array.isArray(run.results)) {
    fail(`SARIF file at '${target}' has malformed results.`);
  }
  return run.results.length;
}

const raw = readReport(sarifPath);
const doc = parseReport(raw, sarifPath);
checkDocument(doc, sarifPath);

let resultCount = 0;
doc.runs.forEach((run, index) => {
  if (!run || typeof run !== 'object' || Array.isArray(run)) {
    fail(`SARIF file at '${sarifPath}' has a malformed run ${index}.`);
  }
  checkTool(run, index, sarifPath);
  checkInvocations(run, index, sarifPath);
  resultCount += countResults(run, index, sarifPath);
});

console.log(
  `VALIDATED ${sarifPath} ` +
    `(sarif ${doc.version}, runs=${doc.runs.length}, ` +
    `results=${resultCount})`,
);

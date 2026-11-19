/** Real paragraph splitter behind the DailyNote copy dialog (design D5/D6). */
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(
  path.resolve(__dirname, "../../..", "assets/js/dailynote-chunks.js"), "utf8"
);
const sandbox = { module: { exports: {} } };
vm.runInNewContext(source, sandbox);
const chunks = sandbox.module.exports;
const { HOSPITAL_FIELD_LIMIT, PART_TARGET, MAX_PART_BUTTONS } = chunks;
const { shouldOpenCopyDialog, splitDailyNoteIntoParts } = chunks;

const passed = [], failed = [];

function normalize(raw) {
  return raw.replace(/\r\n/g, "\n").trim();
}

function repeat(character, length) {
  return character.repeat(length);
}

function paragraph(index, length) {
  return repeat(String.fromCharCode(97 + index), length);
}

function partLengths(result) {
  return Array.from(result.parts, (part) => part.text.length);
}

function partSeparators(result) {
  return Array.from(result.parts, (part) => part.separatorToNextPart);
}

function reassemble(shownParts) {
  let text = "";
  shownParts.forEach((part, index) => {
    if (index > 0) text += shownParts[index - 1].separatorToNextPart;
    text += part.text;
  });
  return text;
}

function assertPartLimits(parts) {
  parts.forEach((part, index) => {
    assert.ok(
      part.text.length <= HOSPITAL_FIELD_LIMIT,
      "part " + (index + 1) + " has " + part.text.length + " characters"
    );
  });
}

function assertReassembly(raw, result) {
  const rebuilt = reassemble(result.parts.slice(0, MAX_PART_BUTTONS));
  assert.equal(rebuilt.length, result.coveredLength, "covered length");
  assert.ok(normalize(raw).startsWith(rebuilt), "rebuilt prefix");
}

function assertSplitInvariants(raw, result) {
  assertPartLimits(result.parts);
  assert.equal(result.totalLength, normalize(raw).length, "total length");
  assert.equal(
    result.coveredLength + result.uncoveredLength,
    result.totalLength,
    "coverage adds up"
  );
  assert.equal(
    shouldOpenCopyDialog(raw),
    raw.length > HOSPITAL_FIELD_LIMIT,
    "dialog decision follows the raw length"
  );
  assertReassembly(raw, result);
}

function check(name, test) {
  try { test(); passed.push(name); }
  catch (error) { failed.push({ name, error: error.message }); }
}

check("exported limits match the hospital field contract", () => {
  assert.equal(HOSPITAL_FIELD_LIMIT, 4000);
  assert.equal(PART_TARGET, 3900);
  assert.equal(MAX_PART_BUTTONS, 4);
});

check("4000 characters copy directly without a dialog", () => {
  const raw = repeat("a", HOSPITAL_FIELD_LIMIT);
  const result = splitDailyNoteIntoParts(raw);
  assert.equal(shouldOpenCopyDialog(raw), false);
  assert.equal(result.parts.length, 1);
  assert.equal(result.parts[0].text, raw);
  assert.equal(result.totalLength, HOSPITAL_FIELD_LIMIT);
  assert.equal(result.uncoveredLength, 0);
  assertSplitInvariants(raw, result);
});

check("4001 characters open the dialog split at the field limit", () => {
  const raw = repeat("a", HOSPITAL_FIELD_LIMIT + 1);
  const result = splitDailyNoteIntoParts(raw);
  assert.equal(shouldOpenCopyDialog(raw), true);
  assert.deepEqual(partLengths(result), [4000, 1]);
  assert.equal(result.uncoveredLength, 0);
  assertSplitInvariants(raw, result);
});

check("CRLF shrink still opens the dialog with a single part", () => {
  const raw = repeat("a", 2000) + "\r\n" + repeat("b", 1999);
  assert.equal(raw.length, HOSPITAL_FIELD_LIMIT + 1);
  const result = splitDailyNoteIntoParts(raw);
  assert.equal(shouldOpenCopyDialog(raw), true);
  assert.equal(result.totalLength, HOSPITAL_FIELD_LIMIT);
  assert.equal(result.parts.length, 1);
  assert.equal(result.parts[0].text.length, HOSPITAL_FIELD_LIMIT);
  assertSplitInvariants(raw, result);
});

check("multi-paragraph notes break on blank lines", () => {
  const raw = [0, 1, 2, 3].map((index) => paragraph(index, 2000)).join("\n\n");
  const result = splitDailyNoteIntoParts(raw);
  assert.deepEqual(partLengths(result), [2000, 2000, 2000, 2000]);
  result.parts.forEach((part) => {
    assert.ok(!part.text.includes("\n\n"), "part holds one paragraph");
  });
  assert.deepEqual(partSeparators(result), ["\n\n", "\n\n", "\n\n", ""]);
  assert.equal(result.uncoveredLength, 0);
  assertSplitInvariants(raw, result);
});

check("small paragraphs pack into one part up to the target", () => {
  const raw = [0, 1, 2].map((index) => paragraph(index, 1000)).join("\n\n");
  const result = splitDailyNoteIntoParts(raw);
  assert.equal(result.parts.length, 1);
  assert.equal(result.parts[0].text.length, 3000 + 2 * 2);
  assert.ok(result.parts[0].text.length <= PART_TARGET);
  assertSplitInvariants(raw, result);
});

check("oversized paragraph splits by lines keeping newline separators", () => {
  const raw = repeat("a", 2000) + "\n" + repeat("b", 2500);
  const result = splitDailyNoteIntoParts(raw);
  assert.deepEqual(partLengths(result), [2000, 2500]);
  assert.equal(result.parts[0].separatorToNextPart, "\n");
  assertSplitInvariants(raw, result);
});

check("oversized line splits by sentences keeping the space separator", () => {
  const raw = repeat("a", 3000) + ". " + repeat("b", 1000);
  const result = splitDailyNoteIntoParts(raw);
  assert.deepEqual(partLengths(result), [3001, 1000]);
  assert.equal(result.parts[0].separatorToNextPart, " ");
  assertSplitInvariants(raw, result);
});

check("oversized sentence hard-cuts without separators", () => {
  const raw = repeat("z", 9000);
  const result = splitDailyNoteIntoParts(raw);
  assert.deepEqual(partLengths(result), [4000, 4000, 1000]);
  assert.deepEqual(partSeparators(result), ["", "", ""]);
  assertSplitInvariants(raw, result);
});

check("whitespace-only content produces no parts", () => {
  const raw = " \n\n\t\n  ";
  const result = splitDailyNoteIntoParts(raw);
  assert.equal(result.parts.length, 0);
  assert.equal(result.totalLength, 0);
  assert.equal(result.coveredLength, 0);
  assert.equal(result.uncoveredLength, 0);
});

check("five 3000-character paragraphs expose an uncovered remainder", () => {
  const raw = [0, 1, 2, 3, 4].map((index) => paragraph(index, 3000)).join("\n\n");
  const result = splitDailyNoteIntoParts(raw);
  assert.equal(result.totalLength, 15000 + 2 * 4);
  assert.equal(result.parts.length, 5);
  assert.equal(result.coveredLength, 3000 * MAX_PART_BUTTONS + 2 * 3);
  assert.ok(result.uncoveredLength > 0);
  assertSplitInvariants(raw, result);
});

check("notes beyond the 16000 hospital capacity are capped at four parts", () => {
  const paragraphs = Array.from({ length: 10 }, (_, index) => paragraph(index % 10, 2000));
  const raw = paragraphs.join("\n\n");
  const result = splitDailyNoteIntoParts(raw);
  assert.ok(result.totalLength > MAX_PART_BUTTONS * HOSPITAL_FIELD_LIMIT);
  assert.equal(result.parts.length, 10);
  assert.equal(result.coveredLength, 2000 * MAX_PART_BUTTONS + 2 * 3);
  assertSplitInvariants(raw, result);
});

console.log(JSON.stringify({ passed, failed }, null, 2));
process.exitCode = failed.length ? 1 : 0;

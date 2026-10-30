#!/usr/bin/env node
/**
 * Deterministic IPAM disjointness check for the eon migration.
 *
 * Reads a JSON document with `occupied`, `localIntents` and `reserved`
 * arrays of `{ cidr, origin }` entries and verifies, by integer range
 * containment (not only by string equality), that every reserved block
 * is disjoint from:
 *
 *   - every occupied block (eon Docker networks, host LAN, VPN overlay),
 *   - every local inventory intent (infra-single-db), and
 *   - every other reserved block.
 *
 * Exit codes:
 *   0  all reserved blocks are disjoint
 *   1  at least one overlap was found (offending pairs are printed)
 *   2  usage or input-data error
 *
 * No third-party dependencies; IPv4 only, which is all the evidence uses.
 */
import { readFileSync } from 'node:fs';

const EXIT_PASS = 0;
const EXIT_CONFLICT = 1;
const EXIT_ERROR = 2;

const USAGE =
  'usage: node scripts/tests/check_ipam_disjoint.mjs <ipam-networks.json>';

class InputError extends Error {}

function die(message) {
  throw new InputError(message);
}

function parseIpv4(text) {
  const parts = text.split('.');
  if (parts.length !== 4) return null;
  let value = 0;
  for (const part of parts) {
    if (!/^\d{1,3}$/.test(part)) return null;
    const octet = Number(part);
    if (octet > 255) return null;
    value = value * 256 + octet;
  }
  return value;
}

function formatIpv4(value) {
  return [
    Math.floor(value / 16777216) % 256,
    Math.floor(value / 65536) % 256,
    Math.floor(value / 256) % 256,
    value % 256,
  ].join('.');
}

function parseCidr(raw, label) {
  if (typeof raw !== 'string') {
    die(`${label}: cidr must be a string`);
  }
  const match = /^(\d{1,3}(?:\.\d{1,3}){3})\/(\d{1,2})$/.exec(raw.trim());
  if (!match) {
    die(`${label}: invalid CIDR ${JSON.stringify(raw)}`);
  }
  const address = parseIpv4(match[1]);
  const prefix = Number(match[2]);
  if (address === null || prefix > 32) {
    die(`${label}: invalid CIDR ${JSON.stringify(raw)}`);
  }
  const mask = prefix === 0 ? 0 : (0xffffffff << (32 - prefix)) >>> 0;
  const start = (address & mask) >>> 0;
  if (start !== address) {
    die(
      `${label}: CIDR ${JSON.stringify(raw)} has host bits set ` +
        '(not canonical)',
    );
  }
  const size = 2 ** (32 - prefix);
  return {
    cidr: raw.trim(),
    start,
    end: start + size - 1,
    prefix,
    range: `${formatIpv4(start)}-${formatIpv4(start + size - 1)}`,
  };
}

function overlaps(a, b) {
  return a.start <= b.end && b.start <= a.end;
}

function relation(a, b) {
  if (a.start === b.start && a.end === b.end) return 'equal';
  if (a.start >= b.start && a.end <= b.end) return 'contained-by';
  if (b.start >= a.start && b.end <= a.end) return 'contains';
  return 'partial-overlap';
}

function loadSet(document, name) {
  if (!Array.isArray(document[name])) {
    die(`missing array "${name}" in input document`);
  }
  return document[name].map((entry, index) => {
    const label = `${name}[${index}]`;
    if (!entry || typeof entry !== 'object') {
      die(`${label}: entry must be an object`);
    }
    if (typeof entry.origin !== 'string' || entry.origin.length === 0) {
      die(`${label}: origin must be a non-empty string`);
    }
    const parsed = parseCidr(entry.cidr, label);
    return { ...parsed, origin: entry.origin };
  });
}

function wrapText(text, width = 78, indent = '') {
  const words = text.split(/\s+/).filter(Boolean);
  const lines = [];
  let current = '';
  for (const word of words) {
    const candidate = current ? `${current} ${word}` : word;
    if (current && indent.length + candidate.length > width) {
      lines.push(indent + current);
      current = word;
    } else {
      current = candidate;
    }
  }
  if (current) lines.push(indent + current);
  return lines;
}

function renderTable(headers, rows) {
  const widths = headers.map((header, column) =>
    Math.max(
      header.length,
      ...rows.map((row) => String(row[column]).length),
    ),
  );
  const renderRow = (cells) =>
    `| ${cells
      .map((cell, column) => String(cell).padEnd(widths[column]))
      .join(' | ')} |`;
  const separator = `| ${widths.map((width) => '-'.repeat(width)).join(' | ')} |`;
  return [renderRow(headers), separator, ...rows.map(renderRow)].join('\n');
}

function run(inputPath) {
  let document;
  try {
    document = JSON.parse(readFileSync(inputPath, 'utf8'));
  } catch (error) {
    die(`cannot read "${inputPath}": ${error.message}`);
  }

  if (
    document === null ||
    typeof document !== 'object' ||
    Array.isArray(document)
  ) {
    die('input document must be a JSON object');
  }

  const occupied = loadSet(document, 'occupied');
  const localIntents = loadSet(document, 'localIntents');
  const reserved = loadSet(document, 'reserved');
  if (reserved.length === 0) {
    die('"reserved" must contain at least one entry');
  }

  const conflicts = [];
  const conflictCounts = reserved.map(() => 0);

  reserved.forEach((block, index) => {
    const compare = (kind, other) => {
      if (!overlaps(block, other)) return;
      conflicts.push({ kind, block, other, relation: relation(block, other) });
      conflictCounts[index] += 1;
    };
    occupied.forEach((other) => compare('occupied', other));
    localIntents.forEach((other) => compare('localIntents', other));
    reserved.forEach((other, otherIndex) => {
      if (otherIndex <= index || !overlaps(block, other)) return;
      conflicts.push({
        kind: 'reserved',
        block,
        other,
        relation: relation(block, other),
      });
      conflictCounts[index] += 1;
      conflictCounts[otherIndex] += 1;
    });
  });

  const lines = [];
  lines.push('IPAM disjointness check');
  lines.push(`input: ${inputPath}`);
  lines.push(
    `sets: occupied=${occupied.length} localIntents=${localIntents.length} reserved=${reserved.length}`,
  );
  lines.push('');
  lines.push(
    renderTable(
      ['#', 'reserved CIDR', 'integer range', 'conflicts'],
      reserved.map((block, index) => [
        index + 1,
        block.cidr,
        block.range,
        conflictCounts[index],
      ]),
    ),
  );

  if (conflicts.length === 0) {
    lines.push('');
    lines.push(
      ...wrapText(
        `result: PASS - ${reserved.length} reserved blocks disjoint from ` +
          `${occupied.length} occupied, ${localIntents.length} local intents ` +
          'and each other (exit 0)',
      ),
    );
    console.log(lines.join('\n'));
    process.exitCode = EXIT_PASS;
    return;
  }

  lines.push('');
  lines.push(`CONFLICTS (${conflicts.length})`);
  conflicts.forEach((conflict, index) => {
    const wrapped = wrapText(
      `${index + 1}. reserved ${conflict.block.cidr} ` +
        `[${conflict.block.origin}] <> ${conflict.kind} ` +
        `${conflict.other.cidr} [${conflict.other.origin}]`,
    );
    lines.push(wrapped[0]);
    wrapped.slice(1).forEach((line) => lines.push(`   ${line}`));
    lines.push(`   relation: ${conflict.relation}`);
  });
  lines.push('');
  lines.push(
    ...wrapText(
      `result: FAIL - ${conflicts.length} overlap(s) found among reserved ` +
        'blocks (exit 1)',
    ),
  );
  console.log(lines.join('\n'));
  process.exitCode = EXIT_CONFLICT;
}

function main() {
  const inputPath = process.argv[2];
  try {
    if (!inputPath) {
      die('missing input path');
    }
    run(inputPath);
  } catch (error) {
    if (error instanceof InputError) {
      console.error(`check_ipam_disjoint: ${error.message}`);
      console.error(USAGE);
      process.exitCode = EXIT_ERROR;
      return;
    }
    throw error;
  }
}

main();

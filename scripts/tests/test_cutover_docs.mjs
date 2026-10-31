import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..');
const cutoverDir = path.join(repoRoot, 'deploy/eon/cutover');
const docs = {
  runbook: path.join(cutoverDir, 'runbook.md'),
  rollback: path.join(cutoverDir, 'rollback.md'),
  checklist: path.join(cutoverDir, 'checklist.md'),
};
const CRON_JOBS = [
  'update_dashboard_stats',
  'update_ward_mapping_cache',
  'check_user_expiration',
  'send_expiration_notifications',
  'lifecycle_report',
];

function read(file) {
  return readFileSync(file, 'utf8');
}

function lines(text) {
  return text.split(/\r?\n/);
}

function gateCount(text) {
  return lines(text).filter((line) => line.startsWith('GATE:')).length;
}

function bashBlocks(text) {
  const result = [];
  const all = lines(text);
  let open = -1;
  for (let index = 0; index < all.length; index += 1) {
    if (all[index].trim() === '```bash') {
      open = index;
    } else if (open !== -1 && all[index].trim() === '```') {
      result.push({ start: open, end: index });
      open = -1;
    }
  }
  return result;
}

test('all three documents exist, are <=450 lines and <=80 columns', () => {
  for (const [name, file] of Object.entries(docs)) {
    const text = read(file);
    const all = lines(text);
    assert.ok(all.length <= 450, `${name} has ${all.length} lines`);
    for (const line of all) {
      assert.ok(line.length <= 80, `${name} line >80: ${line}`);
    }
  }
});

test('runbook has E1 through E9, abort hour 6 and >=2h reserve', () => {
  const text = read(docs.runbook);
  for (let gate = 1; gate <= 9; gate += 1) {
    assert.match(text, new RegExp(`\\bE${gate}\\b`));
  }
  assert.match(text, /<H6>|hora 6/i);
  assert.match(text, /abort/i);
  assert.match(text, /2h|2 horas|duas horas/i);
  assert.match(text, /<TEMPO_s7/);
  assert.match(text, /verify-restore\.sql/);
  assert.match(text, /primeira escrita aceita/i);
  assert.match(text, /cron suspenso|jobs? comentad/i);
});

test('runbook references s4/s5 and gates every bash block', () => {
  const text = read(docs.runbook);
  assert.match(text, /deploy\/eon\/caddy\/apply-and-reverse\.md/);
  assert.match(text, /deploy\/eon\/cron\/install-and-reverse\.md/);
  assert.match(text, /--env-file <REAL_ENV>/);
  const all = lines(text);
  const blocks = bashBlocks(text);
  assert.ok(blocks.length >= 10, `only ${blocks.length} bash blocks`);
  for (const block of blocks) {
    const window = all.slice(Math.max(0, block.start - 8), block.start);
    assert.ok(
      window.some((line) => line.startsWith('GATE:')),
      `bash block at line ${block.start + 1} has no GATE marker`,
    );
  }
});

test('runbook E4 prepares volumes with init before extraction', () => {
  const text = read(docs.runbook);
  const start = text.indexOf('### Passo 5');
  const end = text.indexOf('### Passo 6');
  assert.ok(start !== -1 && end > start);
  const e4 = text.slice(start, end);
  assert.match(e4, /GATE: E4-prepare/);
  assert.match(e4, /GATE: E4-restore/);
  assert.match(e4, /GATE: E4-remap/);
  assert.match(e4, /--no-same-owner/);
  assert.match(e4, /--profile ops run --rm init/);
  assert.match(e4, /9900:9900/);
  assert.match(e4, /PINNED_GNU_TAR_IMAGE/);
  const firstInit = e4.indexOf('--profile ops run --rm init');
  const extract = e4.indexOf('tar --no-same-owner');
  const secondInit = e4.indexOf(
    '--profile ops run --rm init',
    firstInit + 1,
  );
  assert.ok(firstInit !== -1, 'missing pre-extract init');
  assert.ok(extract !== -1, 'missing extraction');
  assert.ok(secondInit !== -1, 'missing post-extract init');
  assert.ok(firstInit < extract, 'extraction before pre-init');
  assert.ok(extract < secondInit, 'missing post-extract init remap');
});

test('runbook documents stop criteria and both rollback regimes', () => {
  const text = read(docs.runbook);
  assert.match(text, /Critérios de parada/i);
  assert.match(text, /hash divergente/i);
  assert.match(text, /restore/i);
  assert.match(text, /CHD, HMD ou Prisma|CHD\/HMD\/Prisma/i);
  assert.match(text, /rollback\.md/);
});

test('runbook freeze SQL, host staging and no-op plan are valid', () => {
  const text = read(docs.runbook);
  assert.match(text, /NOT ILIKE '%pg_stat_activity%'/);
  assert.match(text, /> <ORIGEM_STAGING>\/eqmd-final\.dump/);
  assert.doesNotMatch(text, /-f <ORIGEM_STAGING>/);
  assert.match(text, /manage\.py migrate --plan/);
  assert.match(text, /No planned migration operations/);
  assert.match(text, /PLANO NAO VAZIO/);
  assert.match(text, /GATE: E5-migrate-plan/);
});

test('runbook and checklist verify all five cron jobs by name', () => {
  for (const file of [docs.runbook, docs.checklist]) {
    const text = read(file);
    for (const job of CRON_JOBS) {
      assert.ok(text.includes(job), `${file} missing job ${job}`);
    }
  }
});

test('rollback has pre/post regimes, S1b preflight and no docker start', () => {
  const text = read(docs.rollback);
  assert.match(text, /Rollback pré-escrita/i);
  assert.match(text, /Rollback pós-escrita/i);
  assert.match(text, /Entrypoint|entrypoint/);
  assert.match(text, /migrate/);
  assert.match(text, /S1b/);
  assert.match(text, /escritor único|exatamente um escritor/i);
  assert.match(text, /JAMAIS|nunca descartar/i);
  assert.match(text, /novo login/i);
  assert.match(text, /2 horas|2h/i);
  const commandedStart = lines(text).filter((line) =>
    /^\s*docker\s+start\b/.test(line),
  );
  assert.deepEqual(commandedStart, [], 'unconditional docker start found');
});

test('rollback freezes app writes before cron and restores media+DB', () => {
  const text = read(docs.rollback);
  for (const token of [
    'COMANDO_MANUTENCAO_APROVADO',
    'COMANDO_MANUTENCAO_NOVO_APROVADO',
    'eqmd-media-pos-escrita.tgz',
    'tar --no-same-owner -C /media',
    '-xzf /in/eqmd-media-pos-escrita.tgz',
    '--no-same-owner',
    '> /srv/apps/eqmd/rollback/eqmd-pos-escrita.dump',
    '<ORIGEM_STAGING>/eqmd-pos-escrita.dump',
    'sha256sum -c eqmd-pos-escrita.sha256',
  ]) {
    assert.ok(text.includes(token), `rollback missing ${token}`);
  }
  assert.doesNotMatch(
    text,
    /-f \/srv\/apps\/eqmd\/rollback\/eqmd-pos-escrita\.dump/,
  );
  const freeze = text.indexOf('COMANDO_MANUTENCAO_APROVADO');
  const cronDisable = text.indexOf('# EQMD_JOB \\1');
  const originStart = text.indexOf('up -d --no-deps <ORIGEM_APP>');
  assert.ok(freeze !== -1, 'missing executable app freeze');
  assert.ok(cronDisable !== -1, 'missing eon cron disable');
  assert.ok(originStart !== -1, 'missing origin reactivation');
  assert.ok(cronDisable < originStart, 'origin started before eon cron off');
  const post = text.slice(text.indexOf('## 3. Rollback pós-escrita'));
  const postFreeze = post.indexOf('COMANDO_MANUTENCAO_APROVADO');
  const postCron = post.indexOf('# EQMD_JOB \\1');
  assert.ok(postFreeze !== -1 && postCron !== -1);
  assert.ok(postFreeze < postCron, 'post-write cron disabled before freeze');
});

test('rollback restores into a fresh eqmd_rollback_<ts> and gates swap', () => {
  const text = read(docs.rollback);
  for (const token of [
    'eqmd_rollback_',
    'RB-POS-2a',
    'RB-POS-2b',
    'RB-POS-2c',
    '<ROLLBACK_DB>',
    'ALTER DATABASE',
    'eqmd_pre_rollback_',
    '-d <ROLLBACK_DB>',
  ]) {
    assert.ok(text.includes(token), `rollback missing ${token}`);
  }
  assert.doesNotMatch(
    text,
    /pg_restore[\s\S]{0,180}-d <ORIGEM_DB_NAME>/,
  );
});

test('checklist covers section 9 acceptance and phase F observation', () => {
  const text = read(docs.checklist);
  for (const term of [
    /TLS/,
    /login/i,
    /CSRF/,
    /upload/i,
    /PDF/i,
    /vídeo/i,
    /mídia protegida/i,
    /e-mail/i,
    /service worker|sw\.js/i,
    /manifest/i,
    /redirect|redirecionamento/i,
    /CHD/,
    /HMD/,
    /Prisma/,
    /origem única|uma origem/i,
    /backup/i,
    /restore/i,
  ]) {
    assert.match(text, term);
  }
  assert.match(text, /14 dias/);
  assert.match(text, /24h|24 h/i);
  assert.match(text, /rotina manual/i);
  assert.match(text, /HTTPS do domínio antigo|HTTPS antigo/i);
});

test('every document is gated per command block', () => {
  for (const [name, file] of Object.entries(docs)) {
    const text = read(file);
    const all = lines(text);
    const blocks = bashBlocks(text);
    assert.ok(blocks.length > 0, `${name} has no bash block`);
    for (const block of blocks) {
      const window = all.slice(Math.max(0, block.start - 8), block.start);
      assert.ok(
        window.some((line) => line.startsWith('GATE:')),
        `${name} bash block at line ${block.start + 1} has no GATE`,
      );
    }
  }
});

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import {
  cpSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  writeFileSync,
} from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const testSource = fileURLToPath(import.meta.url);
const repoRoot = path.resolve(path.dirname(testSource), '..', '..');
const evidenceRoot = path.join(repoRoot, 'temp', 'security-hardening', 's1a');
mkdirSync(evidenceRoot, { recursive: true });
// Isolate invocations as well as builds, so concurrent suites cannot collide.
const fixtureRoot = mkdtempSync(path.join(evidenceRoot, 'suite-'));

// Synthetic sentinels only. Content never holds a real secret.
const PROHIBITED = [
  '.env',
  '.env.production',
  '.env.backup',
  'firebase-key.json',
  'credentials.json',
  'config/credentials.json',
  'config/service-account.json',
  'id_rsa',
  'config/tls.pem',
  'config/tls.key',
  'certs/private.p12',
  'matrix/signing.key',
  'matrix/homeserver.yaml',
  'matrix/logs/homeserver.log.2026-08-06',
  'backup.sql',
  'backups/db.dump',
  'archive.bak',
  'app.log',
  'logs/app.log',
  'media/local.jpg',
  'temp/evidence.txt',
  'temp/security/report.txt',
];

// Keep legitimate resources, including Matrix code and its unrendered template.
const CONTROLS = [
  'manage.py',
  'config/settings.py',
  'config/secrets_utils.py',
  'apps/core/key_utils.py',
  'apps/matrix_integration/services.py',
  'apps/patients/models.py',
  'matrix/modules/sample_module.py',
  'matrix/homeserver.yaml.template',
  'assets/index.js',
  'templates/base.html',
  'pyproject.toml',
  'uv.lock',
  'package.json',
  'webpack.config.js',
  'fixtures/sample.json',
];

function docker(args) {
  return execFileSync('docker', args, {
    encoding: 'utf8',
    timeout: 180_000,
    stdio: ['ignore', 'pipe', 'pipe'],
  });
}

function cleanupDocker(args) {
  try {
    docker(args);
  } catch (error) {
    console.warn(`Synthetic Docker cleanup failed: ${error.message}`);
  }
}

function createRun() {
  mkdirSync(fixtureRoot, { recursive: true });
  const root = mkdtempSync(path.join(fixtureRoot, 'run-'));
  const identity = `${process.pid}-${path.basename(root)}`;
  return {
    root,
    contextDir: path.join(root, 'context'),
    dockerfile: path.join(root, 'Dockerfile.proof'),
    artifactTar: path.join(root, 'artifact.tar'),
    listingPath: path.join(root, 'artifact-files.txt'),
    recordPath: path.join(root, 'evidence.json'),
    tag: `eqmd-s1a-context-proof:${identity}`,
    container: `eqmd-s1a-context-proof-${identity}`,
  };
}

function writeFixture(run, relative, content) {
  const target = path.join(run.contextDir, relative);
  mkdirSync(path.dirname(target), { recursive: true });
  writeFileSync(target, content);
}

function prepareFixture(run) {
  for (const relative of PROHIBITED) {
    writeFixture(run, relative, `SYNTHETIC-SENTINEL ${relative}\n`);
  }
  for (const relative of CONTROLS) {
    writeFixture(run, relative, `synthetic control ${relative}\n`);
  }
  cpSync(
    path.join(repoRoot, '.dockerignore'),
    path.join(run.contextDir, '.dockerignore'),
  );
  writeFileSync(
    run.dockerfile,
    'FROM scratch\nCOPY . /ctx\nCMD ["/__s1a_noexec__"]\n',
  );
}

function exportArtifact(run) {
  let imageCreated = false;
  let containerCreated = false;
  try {
    docker(['build', '-t', run.tag, '-f', run.dockerfile, run.contextDir]);
    imageCreated = true;
    run.imageId = docker(['image', 'inspect', run.tag, '--format', '{{.Id}}']).trim();
    docker(['create', '--name', run.container, run.tag]);
    containerCreated = true;
    docker(['export', '-o', run.artifactTar, run.container]);
  } finally {
    if (containerCreated) cleanupDocker(['rm', run.container]);
    if (imageCreated) cleanupDocker(['image', 'rm', run.tag]);
  }
}

function sha256(file) {
  return createHash('sha256').update(readFileSync(file)).digest('hex');
}

function recordEvidence(run, listing) {
  writeFileSync(run.listingPath, listing);
  const record = {
    createdAt: new Date().toISOString(),
    runDirectory: run.root,
    imageId: run.imageId,
    containerStarted: false,
    artifactSha256: sha256(run.artifactTar),
    listingSha256: sha256(run.listingPath),
    ignoreSha256: sha256(path.join(run.contextDir, '.dockerignore')),
    testSourceSha256: sha256(testSource),
    prohibitedCount: PROHIBITED.length,
    controlCount: CONTROLS.length,
  };
  writeFileSync(run.recordPath, `${JSON.stringify(record, null, 2)}\n`);
  console.info(`S1A_EVIDENCE=${run.root}`);
}

function buildFixtureArtifact() {
  const run = createRun();
  prepareFixture(run);
  exportArtifact(run);
  const listing = execFileSync('tar', ['-tf', run.artifactTar], {
    encoding: 'utf8',
    timeout: 60_000,
  });
  recordEvidence(run, listing);
  return new Set(
    listing.split('\n')
      .map((line) => line.trim())
      .filter((line) => line.startsWith('ctx/') && !line.endsWith('/'))
      .map((line) => line.slice('ctx/'.length)),
  );
}

function newRunDirectory(before) {
  const created = readdirSync(fixtureRoot).filter((entry) => !before.has(entry));
  assert.equal(created.length, 1, 'build must allocate exactly one run directory');
  assert.match(created[0], /^run-/);
  return path.join(fixtureRoot, created[0]);
}

function evidenceHashes(directory) {
  return Object.fromEntries(
    ['artifact.tar', 'artifact-files.txt', 'evidence.json']
      .map((name) => [name, sha256(path.join(directory, name))]),
  );
}

test('build context excludes prohibited sentinels and keeps controls', () => {
  let present;
  try {
    present = buildFixtureArtifact();
  } catch (error) {
    const detail = `${error.stdout ?? ''}${error.stderr ?? ''}${error.message}`;
    assert.fail(`Docker builder indisponível ou falhou (bloqueio, não skip): ${detail}`);
  }
  assert.deepEqual(
    {
      leaked: PROHIBITED.filter((relative) => present.has(relative)),
      missing: CONTROLS.filter((relative) => !present.has(relative)),
    },
    { leaked: [], missing: [] },
    `contexto inseguro ou incompleto; ver execuções em ${fixtureRoot}`,
  );
  assert.ok(present.has('manage.py'));
});

test('each build preserves previous evidence and allocates a fresh run', () => {
  mkdirSync(fixtureRoot, { recursive: true });
  const previous = mkdtempSync(path.join(fixtureRoot, 'previous-'));
  const marker = path.join(previous, 'report.txt');
  const content = 'SYNTHETIC EVIDENCE FROM A PREVIOUS RUN\n';
  writeFileSync(marker, content);
  const before = new Set(readdirSync(fixtureRoot));

  buildFixtureArtifact();

  assert.ok(existsSync(marker), 'a new run removed previous evidence');
  assert.equal(readFileSync(marker, 'utf8'), content);
  for (const entry of before) {
    assert.ok(existsSync(path.join(fixtureRoot, entry)), `removed ${entry}`);
  }
  const firstRun = newRunDirectory(before);
  const firstHashes = evidenceHashes(firstRun);
  const beforeSecond = new Set(readdirSync(fixtureRoot));

  buildFixtureArtifact();

  const secondRun = newRunDirectory(beforeSecond);
  assert.notEqual(firstRun, secondRun);
  assert.equal(readFileSync(marker, 'utf8'), content);
  assert.deepEqual(evidenceHashes(firstRun), firstHashes);
});

// ---------------------------------------------------------------------------
// S1b: native runtime, installation cache and locked Python package parity.
// Read-only shell inspection only; Python is never executed in the candidate.
// ---------------------------------------------------------------------------
const s1bRoot = path.join(repoRoot, 'temp', 'security-hardening', 's1b');
const lockSource = readFileSync(path.join(repoRoot, 'uv.lock'), 'utf8');
const securityImage = process.env.EQMD_SECURITY_IMAGE ?? 'eqmd:s1b-candidate';
const sitePackages = '/usr/local/lib/python3.12/site-packages';
const LOCK_TARGETS = ['django', 'djangorestframework', 'pillow', 'certifi', 'gunicorn', 'psycopg2-binary'];
const s1bRecord = { image: securityImage, createdAt: new Date().toISOString() };
let s1bEvidenceDir;
function writeS1bEvidence() {
  if (!s1bEvidenceDir) {
    mkdirSync(s1bRoot, { recursive: true });
    s1bEvidenceDir = mkdtempSync(path.join(s1bRoot, 'native-'));
    console.info(`S1B_EVIDENCE=${s1bEvidenceDir}`);
  }
  writeFileSync(
    path.join(s1bEvidenceDir, 'runtime-evidence.json'),
    `${JSON.stringify(s1bRecord, null, 2)}\n`,
  );
}

function runInImage(script, mounts = []) {
  const args = ['run', '--rm', '--network', 'none'];
  mounts.forEach((mount) => args.push('-v', mount));
  args.push('--entrypoint', 'sh', securityImage, '-c', script);
  return execFileSync('docker', args, {
    encoding: 'utf8', timeout: 180_000, stdio: ['ignore', 'pipe', 'pipe'],
  });
}

function runInImageOrFail(script, mounts = []) {
  try {
    return runInImage(script, mounts);
  } catch (error) {
    const detail = `${error.stdout ?? ''}${error.stderr ?? ''}${error.message}`;
    assert.fail(`imagem ${securityImage} inspecionada falhou: ${detail}`);
  }
}

function dockerInspectImage(format) {
  try {
    return docker(['image', 'inspect', securityImage, '--format', format]).trim();
  } catch (error) {
    assert.fail(`metadata da imagem ${securityImage} indisponível: ${error.message}`);
  }
}

function lockVersion(name) {
  const pattern = `\\[\\[package\\]\\]\\nname = "${name}"\\nversion = "([^"]+)"`;
  const match = lockSource.match(new RegExp(pattern));
  assert.ok(match, `uv.lock sem bloco de pacote para ${name}`);
  return match[1];
}

function syntheticPdf(text) {
  const stream = `BT /F1 14 Tf 20 120 Td (${text}) Tj ET\n`;
  const bodies = [
    '<< /Type /Catalog /Pages 2 0 R >>',
    '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
    '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 200] '
      + '/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>',
    `<< /Length ${stream.length} >>\nstream\n${stream}endstream`,
    '<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
  ];
  let pdf = '%PDF-1.4\n';
  const offsets = [0];
  bodies.forEach((body, index) => {
    offsets.push(pdf.length);
    pdf += `${index + 1} 0 obj\n${body}\nendobj\n`;
  });
  const xref = pdf.length;
  pdf += `xref\n0 ${bodies.length + 1}\n0000000000 65535 f \n`;
  for (let index = 1; index <= bodies.length; index += 1) {
    pdf += `${String(offsets[index]).padStart(10, '0')} 00000 n \n`;
  }
  pdf += `trailer\n<< /Size ${bodies.length + 1} /Root 1 0 R >>\n`;
  return `${pdf}startxref\n${xref}\n%%EOF\n`;
}

test('S1b runtime keeps Debian 13 / Python 3.12 and meets Brotli floor', () => {
  const script = [
    'cat /etc/os-release',
    'echo @@PYTHON_DIRS',
    'ls -d /usr/local/lib/python3.12* 2>/dev/null',
    'echo @@BROTLI',
    "v=$(dpkg-query -W -f='${Version}' libbrotli1); echo \"$v\"",
    "dpkg --compare-versions \"$v\" ge '1.1.0-2+deb13u1'"
      + ' && echo FLOOR_OK || echo FLOOR_FAIL',
  ].join('\n');
  const [osRelease, rest] = runInImageOrFail(script).split('@@PYTHON_DIRS\n');
  const [pythonDirs, brotli] = rest.split('@@BROTLI\n');
  assert.match(osRelease, /PRETTY_NAME="Debian GNU\/Linux 13 \(trixie\)"/);
  assert.match(osRelease, /VERSION_CODENAME=trixie/);
  const dirs = pythonDirs.trim().split('\n').filter(Boolean);
  assert.ok(dirs.length > 0, 'runtime sem /usr/local/lib/python3.12*');
  dirs.forEach((directory) => {
    assert.match(directory, /^\/usr\/local\/lib\/python3\.12/);
  });

  const [version, verdict] = brotli.trim().split('\n');
  assert.match(version, /^\d+\.\d+\.\d+-\d+[^ ]*$/);
  assert.equal(
    verdict,
    'FLOOR_OK',
    `libbrotli1 ${version} abaixo de 1.1.0-2+deb13u1`,
  );
  s1bRecord.base = {
    imageId: dockerInspectImage('{{.Id}}'),
    osRelease: osRelease.trim().split('\n'),
    pythonDirectories: dirs,
    libbrotli1: version,
    brotliFloor: '1.1.0-2+deb13u1',
    brotliVerdict: verdict,
  };
});

test('S1b runtime does not persist installation caches', () => {
  const script = [
    'for p in /root/.cache/uv /root/.cache/pip /tmp/requirements.txt; do',
    '  if [ -e "$p" ]; then echo "PRESENT $p"; fi',
    'done',
    'find /root /home -maxdepth 3 -type d -name uv 2>/dev/null || true',
  ].join('\n');
  const output = runInImageOrFail(script).trim();
  assert.equal(output, '', `cache/artefato de instalação persistido: ${output}`);
});

test('S1b locked Python packages stay installed at lock versions', () => {
  const script = [
    `for d in ${sitePackages}/*.dist-info; do`,
    '  n=$(sed -n "s/^Name: //p" "$d/METADATA" | head -1)',
    '  v=$(sed -n "s/^Version: //p" "$d/METADATA" | head -1)',
    '  echo "$n=$v"',
    'done',
  ].join('\n');
  const installed = new Map(
    runInImageOrFail(script)
      .split('\n')
      .map((line) => line.trim())
      .filter(Boolean)
      .map((line) => {
        const index = line.indexOf('=');
        return [line.slice(0, index).toLowerCase(), line.slice(index + 1)];
      }),
  );

  for (const name of LOCK_TARGETS) {
    assert.equal(
      installed.get(name),
      lockVersion(name),
      `${name} instalado difere do uv.lock`,
    );
  }
  s1bRecord.lockParity = {
    targets: Object.fromEntries(
      LOCK_TARGETS.map((name) => [
        name,
        { installed: installed.get(name), lock: lockVersion(name) },
      ]),
    ),
  };
});

test('S1b native tools, targets and health metadata stay functional', () => {
  mkdirSync(s1bRoot, { recursive: true });
  const smokeDir = mkdtempSync(path.join(s1bRoot, 'smoke-'));
  writeFileSync(
    path.join(smokeDir, 'synthetic.pdf'),
    syntheticPdf('S1B SYNTHETIC PDF'),
  );
  const script = [
    'set -e',
    'ffmpeg -hide_banner -loglevel error -f lavfi '
      + '-i testsrc=duration=1:size=64x64:rate=5 -c:v mpeg4 -y /tmp/s1b.avi',
    'ffmpeg -hide_banner -loglevel error -i /tmp/s1b.avi -f null -',
    'ffprobe -v error -show_entries stream=codec_name '
      + '-of default=nw=1 /tmp/s1b.avi',
    'echo FFMPEG_SMOKE_OK',
    'pdftotext /work/synthetic.pdf -',
    'echo @@PDF_DONE',
    'test -f /app/manage.py && echo MANAGE_OK',
    'test -f /app/config/wsgi.py && echo WSGI_OK',
    'test -d /app/staticfiles && [ -n "$(ls -A /app/staticfiles)" ]'
      + ' && echo STATIC_OK',
    'test -x /usr/local/bin/gunicorn && echo GUNICORN_OK',
  ].join('\n');
  const output = runInImageOrFail(script, [`${smokeDir}:/work:ro`]);
  assert.match(output, /^codec_name=mpeg4$/m);
  assert.match(output, /^FFMPEG_SMOKE_OK$/m);
  assert.match(output, /S1B SYNTHETIC PDF/);
  for (const marker of ['MANAGE_OK', 'WSGI_OK', 'STATIC_OK', 'GUNICORN_OK']) {
    assert.match(output, new RegExp(`^${marker}$`, 'm'));
  }

  const healthcheck = dockerInspectImage('{{json .Config.Healthcheck}}');
  assert.match(healthcheck, /http:\/\/localhost:8000\/health\//);
  const command = dockerInspectImage('{{json .Config.Cmd}}');
  assert.match(command, /gunicorn/);
  const targets = dockerInspectImage('{{json .Config.ExposedPorts}}');
  assert.match(targets, /8000\/tcp/);

  s1bRecord.native = {
    imageId: dockerInspectImage('{{.Id}}'),
    toolOutput: output.trim().split('\n'),
    healthcheck,
    command,
    exposedPorts: targets,
  };
  writeS1bEvidence();
});

import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..');
const composePath = path.join(repoRoot, 'docker-compose.eon.yml');
const envPath = path.join(repoRoot, 'env.eon.example');

const EQMD_IMAGE =
  'ghcr.io/carlosapgomes/eqmd@sha256:' +
  'fe31d296f50dd34c19c437244ea9a3d61f75aba4ec7d806329b50f8340cc4c4f';
const POSTGRES_IMAGE =
  'postgres@sha256:' +
  '1d1095b0503145be79c79239372aefadfacf6b7c33c9245bbf99ce4b6b89c737';
const NETWORKS = [
  '<REDE_INGRESS>',
  '<REDE_APP>',
  '<REDE_DB>',
  '<REDE_EGRESS>',
];

// Every variable config/settings.py reads via os.getenv, plus the
// Compose-level variables used by docker-compose.eon.yml.
const SETTINGS_ENV_VARS = [
  'SECRET_KEY',
  'DEBUG',
  'ALLOWED_HOSTS',
  'SESSION_COOKIE_SECURE',
  'CSRF_COOKIE_SECURE',
  'DJANGO_CSRF_TRUSTED_ORIGINS',
  'SITE_ID',
  'DATABASE_ENGINE',
  'DATABASE_NAME',
  'DATABASE_USER',
  'DATABASE_PASSWORD',
  'DATABASE_HOST',
  'DATABASE_PORT',
  'LANGUAGE_CODE',
  'TIME_ZONE',
  'EMAIL_BACKEND',
  'EMAIL_HOST',
  'EMAIL_PORT',
  'EMAIL_USE_TLS',
  'EMAIL_HOST_USER',
  'EMAIL_HOST_PASSWORD',
  'DEFAULT_FROM_EMAIL',
  'ACCOUNT_EMAIL_VERIFICATION',
  'HOSPITAL_NAME',
  'HOSPITAL_ADDRESS',
  'HOSPITAL_CITY',
  'HOSPITAL_STATE_FULL',
  'HOSPITAL_PHONE',
  'HOSPITAL_EMAIL',
  'HOSPITAL_WEBSITE',
  'HOSPITAL_LOGO_PATH',
  'HOSPITAL_LOGO_URL',
  'HOSPITAL_SHORT_ID',
  'HOSPITAL_CNES',
  'HOSPITAL_CNPJ',
  'HOSPITAL_PDF_FORMS_ENABLED',
  'HOSPITAL_PDF_FORMS_PATH',
  'PDF_FORMS_MAX_FILE_SIZE',
  'PDF_FORMS_REQUIRE_VALIDATION',
  'OIDC_ISSUER',
  'DELEGATED_TOKEN_SECRET',
  'EQMD_FRONTEND_IMAGE',
  'POSTGRES_DB',
  'POSTGRES_USER',
  'POSTGRES_PASSWORD',
  'POSTGRES_ADMIN_PASSWORD',
  'EQMD_USER_PASSWORD',
  'EQMD_MIGRATOR_PASSWORD',
];

let configCache;
let referencedVarsCache;

function runCompose(args) {
  const result = spawnSync(
    'docker',
    ['compose', '-f', composePath, '--env-file', envPath, ...args],
    { cwd: repoRoot, encoding: 'utf8' },
  );
  if (result.error) {
    assert.fail(
      'docker compose config is unavailable; the gate cannot be ' +
        `skipped: ${result.error.message}`,
    );
  }
  return result;
}

function renderConfig() {
  if (configCache) return configCache;
  assert.ok(existsSync(composePath), `missing Compose file: ${composePath}`);
  assert.ok(existsSync(envPath), `missing env template: ${envPath}`);
  const plain = runCompose(['config']);
  assert.equal(
    plain.status,
    0,
    `docker compose config failed (exit ${plain.status}):\n${plain.stderr}`,
  );
  const json = runCompose([
    '--profile',
    'ops',
    'config',
    '--format',
    'json',
  ]);
  assert.equal(
    json.status,
    0,
    `docker compose config --format json failed (exit ${json.status}):\n` +
      json.stderr,
  );
  try {
    configCache = JSON.parse(json.stdout);
  } catch (error) {
    assert.fail(`docker compose config emitted invalid JSON: ${error.message}`);
  }
  return configCache;
}

function envValues() {
  const values = new Map();
  for (const raw of readFileSync(envPath, 'utf8').split(/\r?\n/)) {
    const line = raw.trim();
    if (!line || line.startsWith('#')) continue;
    const separator = line.indexOf('=');
    if (separator === -1) continue;
    values.set(line.slice(0, separator), line.slice(separator + 1));
  }
  return values;
}

function collectVariableReferences(node, found) {
  if (typeof node === 'string') {
    const pattern = /\$\{([A-Za-z_][A-Za-z0-9_]*)/g;
    let match = pattern.exec(node);
    while (match !== null) {
      found.add(match[1]);
      match = pattern.exec(node);
    }
  } else if (Array.isArray(node)) {
    for (const item of node) collectVariableReferences(item, found);
  } else if (node && typeof node === 'object') {
    for (const [key, value] of Object.entries(node)) {
      collectVariableReferences(key, found);
      collectVariableReferences(value, found);
    }
  }
  return found;
}

function composeVariableReferences() {
  if (referencedVarsCache) return referencedVarsCache;
  const rendered = runCompose([
    '--profile',
    'ops',
    'config',
    '--no-interpolate',
    '--format',
    'json',
  ]);
  assert.equal(
    rendered.status,
    0,
    `docker compose config --no-interpolate failed (exit ${rendered.status}):\n` +
      rendered.stderr,
  );
  let parsed;
  try {
    parsed = JSON.parse(rendered.stdout);
  } catch (error) {
    assert.fail(`no-interpolate config emitted invalid JSON: ${error.message}`);
  }
  assert.ok(parsed.services, 'no-interpolate config has no services');
  // Scan the entire rendered text so command/volume/label interpolation is
  // covered too, not only environment and image strings.
  const found = collectVariableReferences(rendered.stdout, new Set());
  referencedVarsCache = found;
  return found;
}

function networkNames(service) {
  return Object.keys(service.networks ?? {}).sort();
}

function volumeMounts(service) {
  return (service.volumes ?? []).map((volume) => {
    if (typeof volume === 'string') {
      const [source, target, mode = ''] = volume.split(':');
      return { source, target, readOnly: mode === 'ro' };
    }
    return {
      source: volume.source,
      target: volume.target,
      readOnly: volume.read_only === true,
    };
  });
}

function findMount(service, source) {
  return volumeMounts(service).find((mount) => mount.source === source);
}

test('a) docker compose config renders with synthetic env', () => {
  const config = renderConfig();
  assert.ok(config.services, 'rendered config has no services');
  for (const name of ['eqmd', 'postgres', 'frontend', 'init', 'migrate']) {
    assert.ok(config.services[name], `missing service: ${name}`);
  }
});

test('b) no service publishes host ports', () => {
  const config = renderConfig();
  for (const [name, service] of Object.entries(config.services)) {
    assert.ok(
      !service.ports || service.ports.length === 0,
      `${name} publishes host ports`,
    );
  }
});

test('c) the four networks are external and no default network exists', () => {
  const config = renderConfig();
  const declared = Object.keys(config.networks ?? {}).sort();
  assert.deepEqual(declared, [...NETWORKS].sort());
  for (const name of NETWORKS) {
    assert.equal(
      config.networks[name].external,
      true,
      `${name} must be external`,
    );
  }
});

test('d) images are pinned by digest / mandatory env', () => {
  const config = renderConfig();
  assert.equal(config.services.eqmd.image, EQMD_IMAGE);
  assert.equal(config.services.postgres.image, POSTGRES_IMAGE);
  assert.equal(
    config.services.frontend.image,
    envValues().get('EQMD_FRONTEND_IMAGE'),
    'frontend image must come from EQMD_FRONTEND_IMAGE',
  );
});

test('e) eqmd runs as dedicated non-root UID/GID 9900', () => {
  const config = renderConfig();
  const user = String(config.services.eqmd.user ?? '');
  const [uid, gid] = user.split(':');
  assert.ok(uid && uid !== '0' && uid !== 'root', `root uid: ${user}`);
  assert.equal(uid, '9900');
  assert.equal(gid, '9900');
});

test('f) migrate/init are ops-only and never run at web startup', () => {
  const config = renderConfig();
  const eqmd = config.services.eqmd;
  const startup = JSON.stringify([eqmd.command, eqmd.entrypoint]);
  assert.ok(
    !/migrate/i.test(startup),
    'eqmd command/entrypoint must not run migrate',
  );

  // Defense in depth: the database service must not run migrate at startup.
  const postgres = config.services.postgres;
  const postgresStartup = JSON.stringify([
    postgres.command,
    postgres.entrypoint,
  ]);
  assert.ok(
    !/migrate/i.test(postgresStartup),
    'postgres command/entrypoint must not run migrate',
  );

  // Both one-shot operations must stay behind the explicit ops profile.
  for (const name of ['init', 'migrate']) {
    const service = config.services[name];
    assert.deepEqual(
      service.profiles,
      ['ops'],
      `${name} must only use the ops profile`,
    );
    assert.equal(service.restart, 'no', `${name} must be one-shot`);
  }
  assert.match(
    JSON.stringify(config.services.migrate.command),
    /migrate/,
    'migrate service must run manage.py migrate',
  );
});

test('g) volumes media/logs/pgdata/static are declared and mounted', () => {
  const config = renderConfig();
  assert.deepEqual(
    Object.keys(config.volumes ?? {}).sort(),
    ['eqmd_logs', 'eqmd_media', 'eqmd_pgdata', 'eqmd_static'].sort(),
  );
  assert.equal(
    findMount(config.services.eqmd, 'eqmd_media')?.target,
    '/app/media',
  );
  assert.equal(
    findMount(config.services.eqmd, 'eqmd_logs')?.target,
    '/app/logs',
  );
  assert.equal(
    findMount(config.services.postgres, 'eqmd_pgdata')?.target,
    '/var/lib/postgresql/data',
  );
  const staticMount = findMount(config.services.frontend, 'eqmd_static');
  assert.ok(staticMount, 'frontend must mount eqmd_static');
  assert.equal(staticMount.readOnly, true, 'eqmd_static must be read-only');
});

test('h) eqmd hardening is enabled; postgres keeps entrypoint caps', () => {
  const config = renderConfig();
  const eqmd = config.services.eqmd;
  assert.equal(eqmd.read_only, true);
  assert.ok((eqmd.cap_drop ?? []).includes('ALL'));
  assert.ok(
    (eqmd.security_opt ?? []).includes('no-new-privileges:true'),
  );
  assert.match(JSON.stringify(eqmd.tmpfs ?? []), /\/tmp/);
  const health = JSON.stringify(eqmd.healthcheck?.test ?? []);
  assert.ok(health.includes('python'), 'eqmd healthcheck must use python');
  assert.ok(!health.includes('curl'), 'eqmd healthcheck must not use curl');

  const postgres = config.services.postgres;
  assert.ok(
    !(postgres.cap_drop ?? []).includes('ALL'),
    'postgres must not drop ALL: entrypoint adjusts ownership',
  );
  assert.match(
    JSON.stringify(postgres.healthcheck?.test ?? []),
    /pg_isready/,
  );
});

test('i) network memberships keep the topology minimal', () => {
  const config = renderConfig();
  assert.deepEqual(networkNames(config.services.eqmd), [
    '<REDE_APP>',
    '<REDE_DB>',
    '<REDE_EGRESS>',
  ]);
  assert.deepEqual(networkNames(config.services.postgres), [
    '<REDE_DB>',
  ]);
  assert.deepEqual(networkNames(config.services.frontend), [
    '<REDE_APP>',
    '<REDE_INGRESS>',
  ]);
  for (const name of ['init', 'migrate']) {
    const nets = networkNames(config.services[name]);
    assert.ok(nets.length > 0, `${name} must join a network`);
    assert.ok(
      nets.every((net) => NETWORKS.includes(net)),
      `${name} joins a non-eqmd network`,
    );
  }
});

test('j) env template is complete, synthetic and comment-safe', () => {
  const raw = readFileSync(envPath, 'utf8');
  const values = envValues();
  const missing = SETTINGS_ENV_VARS.filter((name) => !values.has(name));
  assert.deepEqual(missing, [], `missing env template keys: ${missing}`);
  assert.equal(values.get('TIME_ZONE'), 'America/Bahia');
  assert.equal(values.get('PDF_FORMS_MAX_FILE_SIZE'), '10485760');
  assert.match(values.get('ALLOWED_HOSTS') ?? '', /equipemed\.projetoshgrs\.com/);
  assert.match(
    values.get('DJANGO_CSRF_TRUSTED_ORIGINS') ?? '',
    /https:\/\/equipemed\.projetoshgrs\.com/,
  );
  const inlineComments = raw
    .split(/\r?\n/)
    .filter((line) => line.trim() && !line.trim().startsWith('#'))
    .filter((line) => line.includes('#'));
  assert.deepEqual(
    inlineComments,
    [],
    'env template must not use inline comments after values',
  );
});

test('k) every compose-referenced variable is defined in the env template', () => {
  // Empty on purpose: a ${VAR:-fallback} is not an excuse for a missing
  // template key. Add a name here only with a documented reason.
  const documentedOptional = new Set([]);
  const referenced = [...composeVariableReferences()].sort();
  assert.ok(
    referenced.includes('EQMD_FRONTEND_IMAGE'),
    'image interpolation was not detected',
  );
  assert.ok(
    referenced.includes('EQMD_USER_PASSWORD') &&
      referenced.includes('EQMD_MIGRATOR_PASSWORD') &&
      referenced.includes('POSTGRES_ADMIN_PASSWORD'),
    'nested role-password references were not detected',
  );
  assert.ok(
    referenced.includes('POSTGRES_PASSWORD'),
    'nested fallback reference was not detected',
  );
  const values = envValues();
  const missing = referenced.filter(
    (name) => !values.has(name) && !documentedOptional.has(name),
  );
  assert.deepEqual(
    missing,
    [],
    `compose references env vars missing from the template: ${missing}`,
  );
});

test('l) migrate uses eqmd_migrator, never the runtime role', () => {
  const config = renderConfig();
  const migrateEnv = config.services.migrate.environment ?? {};
  const runtimeEnv = config.services.eqmd.environment ?? {};
  const values = envValues();
  const migratorPassword = values.get('EQMD_MIGRATOR_PASSWORD');
  const userPassword = values.get('EQMD_USER_PASSWORD');

  assert.equal(
    migrateEnv.DATABASE_USER,
    'eqmd_migrator',
    'migrate must authenticate as eqmd_migrator',
  );
  assert.notEqual(migrateEnv.DATABASE_USER, 'eqmd_user');
  assert.equal(
    migrateEnv.DATABASE_PASSWORD,
    migratorPassword,
    'migrate must use the migrator password, not the runtime fallback',
  );
  assert.notEqual(
    migrateEnv.DATABASE_PASSWORD,
    userPassword,
    'migrate password still falls back to the runtime role',
  );
  assert.equal(
    runtimeEnv.DATABASE_USER,
    'eqmd_user',
    'web/runtime service must stay eqmd_user',
  );
});

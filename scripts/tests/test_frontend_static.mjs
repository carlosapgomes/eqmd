import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..');
const nginxPath = path.join(repoRoot, 'deploy/eon/frontend/nginx.conf');
const composePath = path.join(repoRoot, 'docker-compose.eon.yml');
const envPath = path.join(repoRoot, 'env.eon.example');
const caddyPath = path.join(repoRoot, 'deploy/eon/caddy/equipemed.caddyfile.example');
const runbookPath = path.join(
  repoRoot,
  'deploy/eon/caddy/apply-and-reverse.md',
);

function read(file) {
  return readFileSync(file, 'utf8');
}

function block(source, marker) {
  const start = source.indexOf(marker);
  assert.notEqual(start, -1, `missing block: ${marker}`);
  const open = source.indexOf('{', start);
  let depth = 0;
  for (let index = open; index < source.length; index += 1) {
    if (source[index] === '{') depth += 1;
    if (source[index] === '}') {
      depth -= 1;
      if (depth === 0) return source.slice(start, index + 1);
    }
  }
  assert.fail(`unterminated block: ${marker}`);
}

test('nginx config keeps the 60m upload limit and upstream', () => {
  const nginx = read(nginxPath);
  assert.match(nginx, /client_max_body_size\s+60m;/);
  assert.match(nginx, /upstream\s+eqmd_backend\s*\{[^}]*eqmd:8000/);
});

test('service worker and dynamic manifest are no-cache', () => {
  const nginx = read(nginxPath);
  const sw = block(nginx, 'location = /static/sw.js');
  assert.match(sw, /alias\s+\/srv\/eqmd\/static\/sw\.js;/);
  assert.match(sw, /Cache-Control\s+"no-cache[^"]*"/);
  assert.match(sw, /default_type\s+text\/javascript;/);
  assert.match(sw, /text\/javascript\s+js;/);
  assert.match(sw, /Service-Worker-Allowed\s+"\/"/);

  const manifest = block(nginx, 'location = /manifest.json');
  assert.match(manifest, /proxy_pass\s+http:\/\/eqmd_backend;/);
  assert.match(manifest, /Cache-Control\s+"no-cache[^"]*"/);
});

test('/static/ is served from the volume and /media/ is proxy-only', () => {
  const nginx = read(nginxPath);
  const statics = block(nginx, 'location /static/');
  assert.match(statics, /alias\s+\/srv\/eqmd\/static\//);
  assert.doesNotMatch(statics, /proxy_pass/);

  const media = block(nginx, 'location /media/');
  assert.match(media, /proxy_pass\s+http:\/\/eqmd_backend;/);
  assert.doesNotMatch(media, /\b(root|alias)\s+/);
});

test('remaining paths proxy to Django with forwarded headers', () => {
  const nginx = read(nginxPath);
  const root = block(nginx, 'location / {');
  assert.match(root, /proxy_pass\s+http:\/\/eqmd_backend;/);
  assert.match(root, /X-Forwarded-For\s+\$proxy_add_x_forwarded_for/);
  assert.match(root, /X-Forwarded-Proto\s+\$forwarded_proto/);
  assert.match(root, /X-Forwarded-Host\s+\$host/);
  assert.match(nginx, /map\s+\$http_x_forwarded_proto\s+\$forwarded_proto/);
});

test('compose pins nginx by digest and mounts config/static read-only', () => {
  const compose = read(composePath);
  assert.match(compose, /image:\s*nginx@sha256:[0-9a-f]{64}/);
  assert.doesNotMatch(compose, /EQMD_FRONTEND_IMAGE/);
  assert.match(
    compose,
    /\.\/deploy\/eon\/frontend\/nginx\.conf:\/etc\/nginx\/nginx\.conf:ro/,
  );
  assert.match(compose, /eqmd_static:\/srv\/eqmd\/static:ro/);
});

test('init still populates eqmd_static and env has no frontend image', () => {
  const compose = read(composePath);
  const env = read(envPath);
  assert.match(compose, /collectstatic --clear --noinput/);
  assert.match(compose, /eqmd_static:\/app\/staticfiles/);
  assert.doesNotMatch(env, /^EQMD_FRONTEND_IMAGE=/m);
});

test('caddy snippet routes the EQMD hostname over HTTP to frontend:80', () => {
  const caddy = read(caddyPath);
  assert.match(caddy, /http:\/\/equipemed\.projetoshgrs\.com\s*\{/);
  assert.match(caddy, /reverse_proxy\s+frontend:80/);
  assert.match(caddy, /<REDE_INGRESS>/);
  assert.doesNotMatch(caddy, /tls\s+internal/);
});

test('runbook covers baseline, backup, admin-off recreate, smoke and reversal', () => {
  const runbook = read(runbookPath);
  assert.match(runbook, /admin off/i);
  assert.match(runbook, /docker compose/i);
  assert.match(runbook, /--force-recreate/);
  assert.match(runbook, /caddy validate/i);
  assert.match(runbook, /CHD/i);
  assert.match(runbook, /HMD/i);
  assert.match(runbook, /Prisma|<APP_VIZINHA>/i);
  assert.match(runbook, /revers[aã]o|rollback/i);
  assert.match(runbook, /Cloudflare/i);
});

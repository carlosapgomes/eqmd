#!/usr/bin/env node
/**
 * Disposable frontend rehearsal for slice s4.
 *
 * Starts eqmd_s4_* only: nginx pinned by digest + Python stub backend +
 * synthetic static volume. Proves 60m upload limit (413 at 61 MB), PWA
 * no-cache headers, static content types, proxy pass-through, and that
 * /media/ reaches the backend instead of the disk. Always cleans up.
 */
import { spawnSync } from 'node:child_process';
import { mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, '..', '..');
const nginxConf = path.join(repoRoot, 'deploy/eon/frontend/nginx.conf');
const evidenceDir = path.join(repoRoot, 'temp/migracao-eon/s4');

const NGINX_IMAGE =
  'nginx@sha256:' +
  '51047bea59fed88fbd1f52565d2f5fabcb82d311cf6c9e507a10ce74bb3bc3f0';
const PYTHON_IMAGE =
  'python:3.12-slim-trixie@sha256:' +
  'aa943ce411423c7582288f18707ff66eddcbaeb510502d747a72aeb34f30d159';
const PREFIX = 'eqmd_s4_';
const suffix =
  process.env.EQMD_S4_RUN_SUFFIX || `${process.pid}-${Date.now()}`;
const networkName = `${PREFIX}net_${suffix}`;
const stubName = `${PREFIX}stub_${suffix}`;
const frontendName = `${PREFIX}frontend_${suffix}`;
const volumeName = `${PREFIX}static_${suffix}`;
const scratch = path.join('/tmp/opencode', `${PREFIX}${suffix}`);
const largeUpload = path.join(scratch, 'upload-61m.bin');

const expected = {
  containers: [stubName, frontendName],
  volumes: [volumeName],
  networks: [networkName],
};
const created = { containers: [], volumes: [], networks: [] };

const STUB_CODE = `
import http.server
import socketserver

class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'

    def _send(self, body, content_type='text/plain; charset=utf-8'):
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.startswith('/media/'):
            self._send(('MEDIA_STUB:' + self.path).encode())
        elif self.path == '/manifest.json':
            self._send(b'{"name":"stub-manifest"}', 'application/manifest+json')
        elif self.path == '/health/':
            self._send(b'OK')
        elif self.path == '/headers':
            body = '|'.join([
                'host=' + self.headers.get('Host', ''),
                'xff=' + self.headers.get('X-Forwarded-For', ''),
                'xfp=' + self.headers.get('X-Forwarded-Proto', ''),
            ])
            self._send(body.encode())
        else:
            self._send(('STUB:' + self.path).encode())

    def do_POST(self):
        length = int(self.headers.get('Content-Length', '0'))
        self.rfile.read(length)
        self._send(('POST_OK:' + str(length)).encode())

    def log_message(self, *args):
        pass

socketserver.TCPServer.allow_reuse_address = True
class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

with Server(('0.0.0.0', 8000), Handler) as server:
    server.serve_forever()
`;

const POPULATE_CODE = `
from pathlib import Path
root = Path('/srv/eqmd/static')
root.mkdir(parents=True, exist_ok=True)
(root / 'app.css').write_text('body { color: #123456; }\\n', encoding='utf-8')
(root / 'sw.js').write_text(
    "self.addEventListener('install', () => {});\\n", encoding='utf-8')
(root / 'manifest.json').write_text(
    '{"name":"static-manifest"}\\n', encoding='utf-8')
`;

function docker(args, options = {}) {
  const result = spawnSync('docker', args, {
    encoding: options.encoding === null ? null : 'utf8',
    input: options.input,
    maxBuffer: 64 * 1024 * 1024,
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

function sleepSync(milliseconds) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, milliseconds);
}

function resourceExists(kind, name) {
  const args =
    kind === 'containers'
      ? ['inspect', '--type', 'container', name]
      : kind === 'volumes'
        ? ['volume', 'inspect', name]
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
  const residue = { containers: [], volumes: [], networks: [] };
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
  for (const name of created.volumes) {
    docker(['volume', 'rm', '-f', name], { allowFailure: true });
  }
  for (const name of created.networks) {
    docker(['network', 'rm', name], { allowFailure: true });
  }
  try {
    rmSync(scratch, { recursive: true, force: true });
  } catch (error) {
    console.error(`[s4] scratch cleanup warning: ${error.message}`);
  }
}

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => {
    cleanup();
    process.exit(130);
  });
}

function curl(url, options = {}) {
  const bodyFile = path.join(scratch, `body-${Date.now()}-${Math.random()}`);
  const headerFile = `${bodyFile}.headers`;
  const args = [
    '-sS',
    '--max-time',
    options.timeout ?? '60',
    '-D',
    headerFile,
    '-o',
    bodyFile,
    '-w',
    '%{http_code}',
  ];
  if (options.method && options.method !== 'GET') {
    args.push('-X', options.method);
  }
  if (options.dataFile) {
    args.push('--data-binary', `@${options.dataFile}`);
  } else if (options.data !== undefined) {
    args.push('--data-binary', options.data);
  }
  args.push(url);
  const result = spawnSync('curl', args, {
    encoding: 'utf8',
    maxBuffer: 16 * 1024 * 1024,
  });
  if (result.error) {
    throw new Error(`curl failed: ${result.error.message}`);
  }
  if (result.status !== 0) {
    throw new Error(`curl ${url} exited ${result.status}: ${result.stderr}`);
  }
  let headers = '';
  try {
    headers = readFileSync(headerFile, 'utf8');
  } catch (error) {
    throw new Error(`curl headers missing for ${url}: ${error.message}`);
  }
  const body = readFileSync(bodyFile, 'utf8');
  const values = new Map();
  for (const line of headers.split(/\r?\n/).slice(1)) {
    const separator = line.indexOf(':');
    if (separator === -1) continue;
    const key = line.slice(0, separator).trim().toLowerCase();
    const value = line.slice(separator + 1).trim();
    values.set(key, values.has(key) ? `${values.get(key)}, ${value}` : value);
  }
  return {
    status: Number(result.stdout.trim()),
    headers: values,
    body,
  };
}

function check(condition, message) {
  if (!condition) throw new Error(message);
}

function waitHttp(url) {
  for (let attempt = 0; attempt < 120; attempt += 1) {
    const result = spawnSync(
      'curl',
      ['-sS', '--max-time', '3', '-o', '/dev/null', '-w', '%{http_code}', url],
      { encoding: 'utf8' },
    );
    if (result.status === 0 && result.stdout.trim() === '200') return;
    sleepSync(1000);
  }
  throw new Error(`frontend did not answer ${url} in 120s`);
}

function rehearse(evidence) {
  mkdirSync(scratch, { recursive: true });
  assertNamesFree();
  console.log('[s4] exact-name check passed; creating disposables');

  docker(['network', 'create', networkName]);
  created.networks.push(networkName);

  docker(['volume', 'create', volumeName]);
  created.volumes.push(volumeName);
  docker([
    'run', '--rm', '-v', `${volumeName}:/srv/eqmd/static`,
    PYTHON_IMAGE, 'python3', '-c', POPULATE_CODE,
  ]);

  docker([
    'run', '-d', '--name', stubName, '--network', networkName,
    '--network-alias', 'eqmd', PYTHON_IMAGE, 'python3', '-c', STUB_CODE,
  ]);
  created.containers.push(stubName);

  docker([
    'run', '-d', '--name', frontendName, '--network', networkName,
    '-p', '127.0.0.1::80',
    '-v', `${nginxConf}:/etc/nginx/nginx.conf:ro`,
    '-v', `${volumeName}:/srv/eqmd/static:ro`,
    NGINX_IMAGE,
  ]);
  created.containers.push(frontendName);

  const portLine = docker(['port', frontendName, '80/tcp']).stdout.trim();
  const hostPort = portLine.split(':').pop();
  check(/^\d+$/.test(hostPort), `could not resolve frontend port: ${portLine}`);
  const base = `http://127.0.0.1:${hostPort}`;
  console.log(`[s4] frontend=${base}`);
  waitHttp(`${base}/health/`);

  const css = curl(`${base}/static/app.css`);
  check(css.status === 200, `static css status=${css.status}`);
  check(
    (css.headers.get('content-type') ?? '').includes('text/css'),
    `static css content-type=${css.headers.get('content-type')}`,
  );
  check(css.body.includes('#123456'), 'static css body mismatch');

  const sw = curl(`${base}/static/sw.js`);
  check(sw.status === 200, `sw.js status=${sw.status}`);
  check(
    (sw.headers.get('cache-control') ?? '').includes('no-cache'),
    `sw.js cache-control=${sw.headers.get('cache-control')}`,
  );
  check(
    (sw.headers.get('content-type') ?? '').includes('text/javascript'),
    `sw.js content-type=${sw.headers.get('content-type')}`,
  );
  check(
    sw.headers.get('service-worker-allowed') === '/',
    'sw.js scope header missing',
  );

  const manifest = curl(`${base}/manifest.json`);
  check(manifest.status === 200, `manifest status=${manifest.status}`);
  check(
    (manifest.headers.get('cache-control') ?? '').includes('no-cache'),
    `manifest cache-control=${manifest.headers.get('cache-control')}`,
  );
  check(
    manifest.body.includes('stub-manifest'),
    'manifest was not proxied to the backend',
  );

  const proxy = curl(`${base}/api/echo?x=1`);
  check(proxy.status === 200, `proxy status=${proxy.status}`);
  check(
    proxy.body === 'STUB:/api/echo?x=1',
    `proxy body=${JSON.stringify(proxy.body)}`,
  );

  const media = curl(`${base}/media/x`);
  check(media.status === 200, `media status=${media.status}`);
  check(
    media.body === 'MEDIA_STUB:/media/x',
    `media was not proxied to the backend: ${JSON.stringify(media.body)}`,
  );

  const forwarded = curl(`${base}/headers`);
  check(
    /xff=[^|]+/.test(forwarded.body),
    `X-Forwarded-For missing: ${forwarded.body}`,
  );
  check(
    forwarded.body.includes('xfp=http'),
    `X-Forwarded-Proto missing: ${forwarded.body}`,
  );

  const small = curl(`${base}/api/echo`, { method: 'POST', data: 'ok' });
  check(small.status === 200, `small POST status=${small.status}`);
  check(small.body === 'POST_OK:2', `small POST body=${small.body}`);

  spawnSync('truncate', ['-s', '61M', largeUpload], { encoding: 'utf8' });
  const large = curl(`${base}/api/echo`, {
    method: 'POST',
    dataFile: largeUpload,
    timeout: '180',
  });
  check(large.status === 413, `61MB POST status=${large.status}`);

  Object.assign(evidence, {
    static_css: { status: css.status, content_type: css.headers.get('content-type') },
    sw: {
      status: sw.status,
      cache_control: sw.headers.get('cache-control'),
      content_type: sw.headers.get('content-type'),
      scope: sw.headers.get('service-worker-allowed'),
    },
    manifest: {
      status: manifest.status,
      cache_control: manifest.headers.get('cache-control'),
      proxied_body: manifest.body,
    },
    proxy: { status: proxy.status, body: proxy.body },
    media: { status: media.status, body: media.body },
    forwarded: forwarded.body,
    small_post: { status: small.status, body: small.body },
    large_post_61m: { status: large.status },
  });
  console.log('[s4] static css=200 text/css');
  console.log(`[s4] sw.js cache-control=${sw.headers.get('cache-control')}`);
  console.log(
    `[s4] manifest cache-control=${manifest.headers.get('cache-control')}`,
  );
  console.log(`[s4] proxy body=${proxy.body}`);
  console.log(`[s4] media body=${media.body}`);
  console.log(`[s4] 61MB POST status=${large.status}`);
  console.log('[s4] all frontend assertions passed');
}

function main() {
  mkdirSync(evidenceDir, { recursive: true });
  const evidence = { nginx_image: NGINX_IMAGE, prefix: PREFIX };
  let failure = null;
  try {
    rehearse(evidence);
  } catch (error) {
    failure = error;
    console.error(`[s4] FAIL: ${error.message}`);
  } finally {
    cleanup();
  }

  const residue = remainingResources();
  evidence.cleanup_residue = residue;
  console.log(`[s4] cleanup residue: ${JSON.stringify(residue)}`);
  try {
    writeFileSync(
      path.join(evidenceDir, 'e2e-metrics.json'),
      `${JSON.stringify(evidence, null, 2)}\n`,
    );
  } catch (error) {
    console.error(`[s4] could not write metrics: ${error.message}`);
  }

  const hasResidue =
    residue.containers.length + residue.volumes.length + residue.networks.length >
    0;
  if (hasResidue) {
    failure = failure ?? new Error('expected eqmd_s4_* names remain');
  }
  if (failure) {
    process.exitCode = 1;
    return;
  }
  console.log('[s4] PASS');
}

main();

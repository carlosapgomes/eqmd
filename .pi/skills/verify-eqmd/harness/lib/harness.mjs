// Journey runner: one browser, one context per signed-in user, trace + report.
import assert from 'node:assert/strict';
import { chromium } from 'playwright';

import { BASE_URL, PASSWORD, RUN_ID } from './config.mjs';
import { ensureEvidence, evidencePath, requireScaffold, writeJson } from './evidence.mjs';

const VIEWPORT = { width: 1440, height: 900 };

function slug(value) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

export async function startJourney({ id, title }) {
  ensureEvidence();
  const scaffold = requireScaffold();
  const browser = await chromium.launch({
    // System Chrome from the host image: no browser download, no bundled build.
    channel: 'chrome',
    headless: true,
  });

  const steps = [];
  const consoleErrors = [];
  const dialogs = [];
  const sessions = new Map();
  const startedAt = new Date();
  let currentStep = null;

  const journey = {
    id,
    title,
    scaffold,
    baseUrl: BASE_URL,
    dialogs,

    async step(name, fn) {
      const step = { name, status: 'passed', startedAt: new Date().toISOString() };
      currentStep = step;
      const started = Date.now();
      try {
        step.evidence = (await fn()) || [];
      } catch (error) {
        step.status = 'failed';
        step.error = error.message;
        step.stack = error.stack;
        throw error;
      } finally {
        step.durationMs = Date.now() - started;
        steps.push(step);
        currentStep = null;
      }
      return step;
    },

    assert(condition, message) {
      assert.ok(condition, message);
    },

    shot(page, name) {
      const target = evidencePath(id, 'screenshots', `${slug(name)}.png`);
      return page.screenshot({ path: target, fullPage: false }).then(() => target);
    },

    /** Open an isolated browser session signed in as `email` (real login form). */
    async open(label, email) {
      const context = await browser.newContext({ viewport: VIEWPORT, baseURL: BASE_URL });
      await context.tracing.start({ screenshots: true, snapshots: true });
      const page = await context.newPage();
      page.on('console', (message) => {
        if (message.type() === 'error') {
          consoleErrors.push({ label, text: message.text().slice(0, 300), url: page.url() });
        }
      });
      // Native dialogs are recorded and accepted: the app uses alert() to block
      // invalid submissions, so an unexpected one is real evidence.
      page.on('dialog', async (dialog) => {
        dialogs.push({ label, type: dialog.type(), message: dialog.message() });
        await dialog.accept();
      });
      await page.goto('/accounts/login/');
      await page.fill('#id_login', email);
      await page.fill('#id_password', PASSWORD);
      await page.click('button[type=submit]');
      await page.waitForURL('**/dashboard/', { timeout: 15000 });
      sessions.set(label, { context, page });
      return page;
    },

    page(label) {
      const session = sessions.get(label);
      assert.ok(session, `no open session labelled ${label}`);
      return session.page;
    },

    async finish({ failed = false } = {}) {
      for (const [label, session] of sessions) {
        try {
          await session.context.tracing.stop({
            path: evidencePath(id, 'traces', `${slug(label)}.zip`),
          });
        } catch {
          // tracing is evidence only; a failed stop must not mask the result
        }
        await session.context.close();
      }
      await browser.close();

      const report = {
        runId: RUN_ID,
        journey: id,
        title,
        baseUrl: BASE_URL,
        startedAt: startedAt.toISOString(),
        finishedAt: new Date().toISOString(),
        status: failed || steps.some((s) => s.status === 'failed') ? 'failed' : 'passed',
        scaffold: {
          patient: scaffold.patient,
          student: scaffold.student.email,
          doctor: scaffold.doctor.email,
        },
        steps,
        consoleErrors,
        dialogs,
      };
      writeJson(`${id}/report.json`, report);
      return report;
    },
  };

  return journey;
}

/** Run a journey script: report written even when a step throws, exit code 1. */
export async function runScript(id, title, body) {
  const journey = await startJourney({ id, title });
  let failed = false;
  try {
    await body(journey);
  } catch (error) {
    failed = true;
    process.stderr.write(`journey ${id} FAILED: ${error.message}\n`);
  }
  const report = await journey.finish({ failed });
  process.stdout.write(
    `journey ${id} ${report.status} (${report.steps.length} steps) -> ${evidencePath(id, 'report.json')}\n`,
  );
  if (report.status !== 'passed') {
    process.exitCode = 1;
  }
  return report;
}

// J4 — discharge report: no finalize button for students, crafted POST is 403.
import { STUDENT_EMAIL } from './lib/config.mjs';
import { runScript } from './lib/harness.mjs';
import { probePatient } from './lib/probe.mjs';

const FIELDS = {
  medical_specialty: 'Clínica Médica',
  problems_and_diagnosis: 'Diagnostico principal de verificacao automatizada.',
  admission_history: 'Historia de internacao de verificacao.',
  exams_list: 'Exames realizados durante a internacao de verificacao.',
  procedures_list: 'Procedimentos realizados durante a internacao.',
  inpatient_medical_history: 'Evolucao hospitalar de verificacao automatizada.',
  discharge_status: 'Paciente estavel no momento da alta.',
  discharge_recommendations: 'Retorno ambulatorial em sete dias.',
};

async function fillDischargeForm(page) {
  await page.fill('input[name="admission_date"]', '2026-11-01');
  await page.fill('input[name="discharge_date"]', '2026-11-05');
  for (const [name, value] of Object.entries(FIELDS)) {
    await page.fill(`[name="${name}"]`, value);
  }
}

await runScript('j4-discharge-finalize-denied', 'Discharge report: student cannot finalize, crafted POST denied', async (j) => {
  const patient = j.scaffold.patient;

  await j.step('student create screen has no Salvar Definitivo', async () => {
    const page = await j.open('student', STUDENT_EMAIL);
    const response = await page.goto(patient.discharge_create_path);
    j.assert(response.status() === 200, `discharge create form not reachable: ${response.status()}`);
    const buttons = (await page.locator('button[type=submit]').allInnerTexts()).map((b) => b.trim());
    j.assert(buttons.length === 1 && buttons[0] === 'Salvar Rascunho', `unexpected buttons: ${JSON.stringify(buttons)}`);
    j.assert((await page.locator('button[name="save_final"]').count()) === 0, 'student must not see save_final');
    await j.shot(page, 'discharge-create-screen');
    return [`buttons=${JSON.stringify(buttons)}`];
  });

  await j.step('crafted POST with save_final is denied (403)', async () => {
    const page = j.page('student');
    await fillDischargeForm(page);
    // Attach the physician-only action to the submission the way a tampered
    // form would, then submit through the real button.
    await page.evaluate(() => {
      const form = document.querySelector('form');
      const input = document.createElement('input');
      input.type = 'hidden';
      input.name = 'save_final';
      input.value = '1';
      form.appendChild(input);
    });
    const [response] = await Promise.all([page.waitForNavigation(), page.click('button[name="save_draft"]')]);
    j.assert(response.status() === 403, `expected 403 for crafted finalize, got ${response.status()}`);
    const body = await page.locator('body').innerText();
    j.assert(body.includes('Acesso Negado'), '403 body missing Acesso Negado');
    await j.shot(page, 'discharge-crafted-post-403');
    return [`POST ${patient.discharge_create_path} with save_final -> 403`];
  });

  await j.step('legitimate draft save persists as a draft', async () => {
    const page = j.page('student');
    await page.goto(patient.discharge_create_path);
    await fillDischargeForm(page);
    await Promise.all([page.waitForNavigation(), page.click('button[name="save_draft"]')]);
    await page.waitForURL(`**${patient.timeline_path}`);
    j.assert((await page.locator('.draft-badge').count()) === 1, 'discharge draft badge missing on timeline');
    await j.shot(page, 'timeline-discharge-draft');

    const db = probePatient('after-j4-draft', patient.id);
    const reports = db.events.filter((event) => event.event_type_label === 'Relatório de Alta');
    j.assert(reports.length === 1, `expected one discharge report, got ${reports.length}`);
    j.assert(reports[0].is_draft === true, 'discharge report was not stored as draft');
    j.assert(reports[0].draft_promoted_by === null, 'student draft must not record an approver');
    return ['draft badge present', `is_draft=${reports[0].is_draft}`, 'author=' + reports[0].created_by];
  });

  await j.step('student review screen of the discharge draft has no finalize', async () => {
    const page = j.page('student');
    await page.click('a[title="Editar rascunho"]');
    await page.waitForURL('**/dischargereports/*/update/');
    j.assert((await page.locator('button[name="save_final"]').count()) === 0, 'student must not see save_final on the update form');
    const buttons = (await page.locator('button[type=submit]').allInnerTexts()).map((b) => b.trim());
    await j.shot(page, 'discharge-draft-review');
    return [`buttons=${JSON.stringify(buttons)}`];
  });
});

// J6 — APAC submission: student saves a draft, then the update view prefills it.
import { STUDENT_EMAIL } from './lib/config.mjs';
import { runScript } from './lib/harness.mjs';
import { probePatient } from './lib/probe.mjs';

const DIAGNOSIS = 'Diagnostico de verificacao APAC criado pelo fluxo real.';
const EDITED = 'Diagnostico de verificacao APAC - linha editada pelo aluno.';

async function pickSuggestion(page, inputSelector, resultsSelector) {
  const input = page.locator(inputSelector).first();
  await input.fill(inputSelector.includes('icd10') ? 'hipertensao' : 'consulta');
  const option = page.locator(`${resultsSelector} .dropdown-item`).first();
  await option.waitFor({ timeout: 15000 });
  const label = (await option.innerText()).split('\n')[0].trim();
  await option.click();
  return label;
}

await runScript('j6-apac-update-prefill', 'APAC draft saves and the update view prefills persisted values', async (j) => {
  const patient = j.scaffold.patient;
  let updateUrl = '';

  await j.step('student saves an APAC form from the capture screen', async () => {
    const page = await j.open('student', STUDENT_EMAIL);
    const response = await page.goto(patient.apac_path);
    j.assert(response.status() === 200, `APAC form not reachable: ${response.status()}`);
    const procedure = await pickSuggestion(page, '.procedure-search-input', '.procedure-results');
    const icd = await pickSuggestion(page, '.icd10-search-input', '#icd10-results-main');
    await page.fill('textarea[name="main_diagnosis"]', DIAGNOSIS);
    await Promise.all([page.waitForNavigation(), page.click('button[type=submit]')]);
    await page.waitForURL('**/pdf-forms/submission/*/');
    const submissionId = page.url().match(/submission\/([0-9a-f-]{36})\//)[1];
    updateUrl = `/pdf-forms/apac/submission/${submissionId}/edit/`;
    j.assert(
      !j.dialogs.some((dialog) => dialog.message.startsWith('Selecione')),
      `form rejected a required selection: ${JSON.stringify(j.dialogs)}`,
    );
    await j.shot(page, 'apac-submission-detail');
    return [`procedure="${procedure}"`, `icd="${icd}"`, `submission=${submissionId}`];
  });

  await j.step('update view prefills the persisted submission', async () => {
    const page = j.page('student');
    const response = await page.goto(updateUrl);
    j.assert(response.status() === 200, `APAC update view not reachable: ${response.status()}`);
    j.assert((await page.locator('[data-draft-supervision-banner]').count()) === 1, 'draft banner missing on update view');
    const buttons = (await page.locator('button[type=submit]').allInnerTexts()).map((b) => b.trim());
    j.assert(buttons.length === 1 && buttons[0] === 'Salvar rascunho', `unexpected buttons: ${JSON.stringify(buttons)}`);
    const values = {
      patient_name: await page.locator('input[name="patient_name"]').inputValue(),
      main_diagnosis: await page.locator('textarea[name="main_diagnosis"]').inputValue(),
      main_procedure: await page.locator('input[name="main_procedure"]').inputValue(),
      main_icd: await page.locator('input[name="main_icd_id"]').inputValue(),
    };
    j.assert(values.patient_name === patient.name, `patient prefill mismatch: ${values.patient_name}`);
    j.assert(values.main_diagnosis === DIAGNOSIS, `diagnosis prefill mismatch: ${values.main_diagnosis}`);
    j.assert(values.main_procedure.length > 0, 'procedure selection not prefilled');
    j.assert(values.main_icd.length > 0, 'ICD selection not prefilled');
    await j.shot(page, 'apac-update-prefilled');
    return [JSON.stringify(values), `buttons=${JSON.stringify(buttons)}`];
  });

  await j.step('edited line persists and re-opens with the new value', async () => {
    const page = j.page('student');
    await page.fill('textarea[name="main_diagnosis"]', EDITED);
    await Promise.all([page.waitForNavigation(), page.click('button[name="save_draft"]')]);
    await page.waitForURL('**/pdf-forms/submission/*/');
    const alerts = (await page.locator('.alert').allInnerTexts()).map((a) => a.trim());
    j.assert(
      alerts.some((text) => text.includes('atualizado com sucesso')),
      `save confirmation missing: ${JSON.stringify(alerts)}`,
    );
    await page.goto(updateUrl);
    j.assert(
      (await page.locator('[data-draft-supervision-banner]').count()) === 1,
      'reopened APAC form is no longer flagged as a supervised draft',
    );
    const reopened = await page.locator('textarea[name="main_diagnosis"]').inputValue();
    j.assert(reopened === EDITED, `edited value not persisted: ${reopened}`);

    const db = probePatient('after-j6-update', patient.id);
    const submissions = db.events.filter((event) => event.event_type_label === 'Formulário PDF');
    j.assert(submissions.length === 1, `expected one PDF submission, got ${submissions.length}`);
    j.assert(submissions[0].is_draft === true, 'APAC submission lost its draft status');
    j.assert(submissions[0].created_by === STUDENT_EMAIL, `author mismatch: ${submissions[0].created_by}`);
    await j.shot(page, 'apac-update-after-edit');
    return [`persisted value="${reopened}"`, `is_draft=${submissions[0].is_draft}`];
  });
});

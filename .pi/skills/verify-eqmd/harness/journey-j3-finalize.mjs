// J3 — doctor finalizes a student draft (covers the J1 create step too).
import { DOCTOR_EMAIL, STUDENT_EMAIL } from './lib/config.mjs';
import { runScript } from './lib/harness.mjs';
import { probePatient } from './lib/probe.mjs';
import { createSimplenote, noteCard } from './lib/actions.mjs';

const NOTE_TEXT = 'VERIFICACAO J3 nota do aluno criada pelo fluxo real da timeline.';

await runScript('j3-doctor-finalizes-draft', 'Doctor opens a student draft and approves it', async (j) => {
  const patient = j.scaffold.patient;
  let editUrl = '';

  await j.step('student creates a SimpleNote from the timeline', async () => {
    const page = await j.open('student', STUDENT_EMAIL);
    await page.goto(patient.timeline_path);
    j.assert((await page.locator('article.timeline-card').count()) === 0, 'scaffold patient must start empty');
    await createSimplenote(page, j.scaffold, NOTE_TEXT);
    await j.shot(page, 'student-timeline-after-create');
    return ['timeline empty before create (scaffold patient)'];
  });

  await j.step('timeline shows the draft badge, age and Revisar link', async () => {
    const page = j.page('student');
    const card = noteCard(page);
    j.assert((await card.count()) === 1, 'expected exactly one note card');
    j.assert(await card.evaluate((el) => el.classList.contains('timeline-card-draft')), 'card lacks timeline-card-draft tint');
    const badge = card.locator('.draft-badge');
    j.assert((await badge.count()) === 1, 'draft badge missing');
    const badgeText = (await badge.innerText()).trim();
    j.assert(/^Rascunho · há /.test(badgeText), `badge text unexpected: ${badgeText}`);
    j.assert((await card.locator('a[aria-label="Revisar rascunho da nota"]').count()) === 1, 'Revisar link missing');
    j.assert((await card.getByText('Salvar definitivo').count()) === 0, 'timeline must not offer one-click approval');
    j.assert((await card.getByText('Aprovar', { exact: true }).count()) === 0, 'timeline must not offer Aprovar');
    return [`badge="${badgeText}"`, 'tint class timeline-card-draft present', 'Revisar link present', 'no one-click approve'];
  });

  await j.step('student review screen offers drafts only (no Salvar definitivo)', async () => {
    const page = j.page('student');
    await page.click('a[aria-label="Revisar rascunho da nota"]');
    await page.waitForURL('**/simplenotes/*/update/');
    editUrl = page.url();
    j.assert((await page.locator('[data-draft-supervision-banner]').count()) === 1, 'draft banner missing');
    const buttons = await page.locator('button[type=submit]').allInnerTexts();
    j.assert(buttons.length === 1 && /Salvar rascunho/.test(buttons[0]), `unexpected student buttons: ${buttons}`);
    j.assert((await page.locator('button[name="save_final"]').count()) === 0, 'student must not see save_final');
    await j.shot(page, 'student-review-screen');
    return [`student buttons=${JSON.stringify(buttons.map((b) => b.trim()))}`, `editUrl=${editUrl}`];
  });

  await j.step('doctor opens the same draft from the timeline', async () => {
    const page = await j.open('doctor', DOCTOR_EMAIL);
    await page.goto(patient.timeline_path);
    j.assert((await page.locator('.draft-badge').count()) === 1, 'doctor must see the student draft');
    await page.click('a[aria-label="Revisar rascunho da nota"]');
    await page.waitForURL('**/simplenotes/*/update/');
    j.assert(page.url() === editUrl, 'doctor must land on the same draft');
    j.assert((await page.locator('[data-draft-supervision-banner]').count()) === 1, 'doctor banner missing');
    const buttons = await page.locator('button[type=submit]').allInnerTexts();
    j.assert((await page.locator('button[name="save_final"]').count()) === 1, 'doctor must see Salvar definitivo');
    await j.shot(page, 'doctor-review-screen');
    return [`doctor buttons=${JSON.stringify(buttons.map((b) => b.trim()))}`];
  });

  await j.step('doctor clicks Salvar definitivo', async () => {
    const page = j.page('doctor');
    await page.click('button[name="save_final"]');
    await page.waitForURL(`**${patient.timeline_path}`);
    j.assert((await page.locator('.draft-badge').count()) === 0, 'draft badge must be gone after approval');
    j.assert((await page.locator('article.timeline-card.timeline-card-draft').count()) === 0, 'tint must be gone');
    j.assert((await page.locator('a[aria-label="Revisar rascunho da nota"]').count()) === 0, 'Revisar must be replaced by Editar');
    const alerts = await page.locator('.alert').allInnerTexts();
    j.assert(
      alerts.some((text) => text.includes('aprovada e registrada no prontuário')),
      `approval message missing: ${JSON.stringify(alerts)}`,
    );
    await j.shot(page, 'timeline-after-approval');
    return [`alerts=${JSON.stringify(alerts.map((a) => a.trim()).filter(Boolean))}`];
  });

  await j.step('database records author kept and approver set', async () => {
    const db = probePatient('after-j3-finalize', patient.id);
    j.assert(db.patient_found === true, 'patient missing in probe');
    const notes = db.events.filter((event) => event.event_type_label === 'Nota/Observação');
    j.assert(notes.length === 1, `expected one simplenote row, got ${notes.length}`);
    const [note] = notes;
    j.assert(note.is_draft === false, 'row still draft in database');
    j.assert(note.created_by === STUDENT_EMAIL, `author changed: ${note.created_by}`);
    j.assert(note.draft_promoted_by === DOCTOR_EMAIL, `approver not recorded: ${note.draft_promoted_by}`);
    j.assert(Boolean(note.draft_promoted_at), 'draft_promoted_at not recorded');
    return [
      `is_draft=${note.is_draft}`,
      `created_by=${note.created_by}`,
      `draft_promoted_by=${note.draft_promoted_by}`,
      `draft_promoted_at=${note.draft_promoted_at}`,
    ];
  });

  await j.step('student is locked out of the finalized note', async () => {
    const page = j.page('student');
    const response = await page.goto(editUrl);
    j.assert(response.status() === 403, `expected 403 after approval, got ${response.status()}`);
    const text = await page.locator('body').innerText();
    j.assert(text.includes('Acesso Negado'), '403 page body missing Acesso Negado');
    await j.shot(page, 'student-403-after-approval');
    return [`GET ${editUrl} -> 403`, 'page shows "Acesso Negado / Permissão Insuficiente"'];
  });
});

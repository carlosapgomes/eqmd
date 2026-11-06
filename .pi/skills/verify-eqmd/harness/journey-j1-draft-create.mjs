// J1 — student creates a SimpleNote and it lands as a supervised draft.
import { STUDENT_EMAIL } from './lib/config.mjs';
import { runScript } from './lib/harness.mjs';
import { probePatient } from './lib/probe.mjs';
import { createSimplenote, noteCard } from './lib/actions.mjs';

const NOTE_TEXT = 'VERIFICACAO J1 nota do aluno; conteudo com mais de dez caracteres.';

await runScript('j1-student-creates-draft', 'Student creates a SimpleNote that persists as a draft', async (j) => {
  const patient = j.scaffold.patient;

  await j.step('create screen offers a single save action', async () => {
    const page = await j.open('student', STUDENT_EMAIL);
    await page.goto(patient.timeline_path);
    await page.click('#createEventDropdownDesktop');
    await page.click(
      `ul[aria-labelledby="createEventDropdownDesktop"] a[href$="/simplenotes/patient/${patient.id}/create/"]`,
    );
    await page.waitForURL('**/simplenotes/patient/**/create/');
    const buttons = await page.locator('button[type=submit]').allInnerTexts();
    j.assert(buttons.length === 1, `expected one submit button, got ${JSON.stringify(buttons)}`);
    j.assert(/Salvar Nota/.test(buttons[0]), `unexpected create button: ${buttons[0]}`);
    j.assert((await page.locator('button[name="save_final"]').count()) === 0, 'create screen must not offer save_final');
    await j.shot(page, 'create-screen');
    return [`buttons=${JSON.stringify(buttons.map((b) => b.trim()))}`];
  });

  await j.step('student saves the note from the create screen', async () => {
    const page = j.page('student');
    await page.locator('.CodeMirror').click();
    await page.keyboard.type(NOTE_TEXT);
    await page.click('button[type=submit]');
    await page.waitForURL(`**${patient.timeline_path}`);
    const alerts = await page.locator('.alert').allInnerTexts();
    j.assert(alerts.some((text) => text.includes('criada com sucesso')), 'success message missing');
    await j.shot(page, 'timeline-after-create');
    return [`alerts=${JSON.stringify(alerts.map((a) => a.trim()).filter(Boolean))}`];
  });

  await j.step('timeline card shows the draft badge, age, tint and Revisar', async () => {
    const page = j.page('student');
    const card = noteCard(page);
    j.assert((await card.count()) === 1, 'expected one note card');
    j.assert(await card.evaluate((el) => el.classList.contains('timeline-card-draft')), 'draft tint missing');
    const badgeText = (await card.locator('.draft-badge').innerText()).trim();
    j.assert(/^Rascunho · há /.test(badgeText), `badge text unexpected: ${badgeText}`);
    j.assert((await card.locator('a[aria-label="Revisar rascunho da nota"]').count()) === 1, 'Revisar link missing');
    j.assert((await card.locator('a[title="Duplicar nota"]').count()) === 0, 'drafts must not be duplicable');
    return [`badge="${badgeText}"`];
  });

  await j.step('draft row persisted with the student as author', async () => {
    const db = probePatient('after-j1-create', patient.id);
    const notes = db.events.filter((event) => event.event_type_label === 'Nota/Observação');
    j.assert(notes.length === 1, `expected one note row, got ${notes.length}`);
    j.assert(notes[0].is_draft === true, 'row was not persisted as a draft');
    j.assert(notes[0].created_by === STUDENT_EMAIL, `author mismatch: ${notes[0].created_by}`);
    j.assert(notes[0].draft_promoted_by === null, 'draft must not have an approver yet');
    return [`is_draft=${notes[0].is_draft}`, `created_by=${notes[0].created_by}`, 'no approver'];
  });

  await j.step('student review screen only offers Salvar rascunho', async () => {
    const page = j.page('student');
    await page.click('a[aria-label="Revisar rascunho da nota"]');
    await page.waitForURL('**/simplenotes/*/update/');
    j.assert((await page.locator('[data-draft-supervision-banner]').count()) === 1, 'supervision banner missing');
    const buttons = (await page.locator('button[type=submit]').allInnerTexts()).map((b) => b.trim());
    j.assert(buttons.length === 1 && buttons[0] === 'Salvar rascunho', `unexpected buttons: ${JSON.stringify(buttons)}`);
    await j.shot(page, 'student-review-screen');
    return [`buttons=${JSON.stringify(buttons)}`];
  });
});

// J2 — drafts-only timeline filter, and the same draft seen by both roles.
import { DOCTOR_EMAIL, STUDENT_EMAIL } from './lib/config.mjs';
import { runScript } from './lib/harness.mjs';
import { createSimplenote, noteCard } from './lib/actions.mjs';

const DRAFT_TEXT = 'VERIFICACAO J2 rascunho do aluno para o filtro de rascunhos.';
const FINAL_TEXT = 'VERIFICACAO J2 nota definitiva criada por medico.';

await runScript('j2-drafts-only-filter', 'Drafts-only filter and role-dependent draft actions', async (j) => {
  const patient = j.scaffold.patient;

  await j.step('doctor creates a definitive note', async () => {
    const page = await j.open('doctor', DOCTOR_EMAIL);
    await page.goto(patient.simplenote_create_path);
    await page.locator('.CodeMirror').click();
    await page.keyboard.type(FINAL_TEXT);
    await page.click('button[type=submit]');
    await page.waitForURL(`**${patient.timeline_path}`);
    j.assert((await page.locator('.draft-badge').count()) === 0, 'a physician-created note must not be a draft');
    return ['physician note persisted as definitive'];
  });

  await j.step('student creates a draft note', async () => {
    const page = await j.open('student', STUDENT_EMAIL);
    await createSimplenote(page, j.scaffold, DRAFT_TEXT);
    j.assert((await page.locator('.draft-badge').count()) === 1, 'student note must carry the draft badge');
    await j.shot(page, 'timeline-mixed');
    return ['one draft, one definitive card on the timeline'];
  });

  await j.step('drafts_only=1 hides the definitive note', async () => {
    const page = j.page('student');
    await page.goto(`${patient.timeline_path}?drafts_only=1`);
    const cards = page.locator('article.timeline-card');
    j.assert((await cards.count()) === 1, `expected only the draft card, got ${await cards.count()}`);
    const text = await cards.first().innerText();
    j.assert(text.includes(DRAFT_TEXT), 'visible card is not the draft');
    j.assert(!(await page.content()).includes(FINAL_TEXT), 'definitive note still rendered under drafts_only');
    j.assert((await page.locator('#oc-drafts_only').isChecked()) === true, 'desktop drafts-only checkbox not checked');
    j.assert((await page.getByText('Ativos').count()) >= 1, 'active-filter badge missing');
    await j.shot(page, 'timeline-drafts-only');
    return ['1 card', 'checkbox #oc-drafts_only checked', 'definitive note absent'];
  });

  await j.step('same draft, role-dependent review actions', async () => {
    const student = j.page('student');
    await student.click('a[aria-label="Revisar rascunho da nota"]');
    await student.waitForURL('**/simplenotes/*/update/');
    const draftUrl = student.url();
    j.assert((await student.locator('[data-draft-supervision-banner]').count()) === 1, 'student banner missing');
    const studentButtons = (await student.locator('button[type=submit]').allInnerTexts()).map((b) => b.trim());
    j.assert(studentButtons.length === 1, `student must only see Salvar rascunho: ${JSON.stringify(studentButtons)}`);

    const doctor = j.page('doctor');
    await doctor.goto(draftUrl);
    j.assert((await doctor.locator('[data-draft-supervision-banner]').count()) === 1, 'doctor banner missing');
    const doctorButtons = (await doctor.locator('button[type=submit]').allInnerTexts()).map((b) => b.trim());
    j.assert(doctorButtons.includes('Salvar definitivo'), `doctor must see Salvar definitivo: ${JSON.stringify(doctorButtons)}`);
    await j.shot(doctor, 'doctor-review-same-draft');
    return [`student=${JSON.stringify(studentButtons)}`, `doctor=${JSON.stringify(doctorButtons)}`];
  });
});

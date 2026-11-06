// Reusable user-path actions shared by the journeys.
// Each function drives the same controls a person clicks; no test-only hooks.

export function noteCard(page) {
  return page.locator('article.timeline-card').filter({ hasText: 'Nota/Obs.' });
}

export async function createSimplenote(page, scaffold, content) {
  await page.goto(scaffold.patient.timeline_path);
  await page.click('#createEventDropdownDesktop');
  await page.click(
    `ul[aria-labelledby="createEventDropdownDesktop"] a[href$="/simplenotes/patient/${scaffold.patient.id}/create/"]`,
  );
  await page.waitForURL('**/simplenotes/patient/**/create/');
  // EasyMDE replaces the textarea with a CodeMirror editor; a person clicks it
  // and types, so the keyboard path is the one exercised here.
  await page.locator('.CodeMirror').click();
  await page.keyboard.type(content);
  await page.click('button[type=submit]');
  await page.waitForURL(`**${scaffold.patient.timeline_path}`);
}

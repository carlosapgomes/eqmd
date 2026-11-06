// J5 — photo draft: FilePond upload, inline view, download denied, hard delete.
import fs from 'node:fs';

import { STUDENT_EMAIL } from './lib/config.mjs';
import { runScript } from './lib/harness.mjs';
import { evidencePath } from './lib/evidence.mjs';
import { probePatient } from './lib/probe.mjs';
const PNG_BASE64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAoAAAAKCAYAAACNMs+9AAAAFUlEQVR42mP8z8BQz0AEYBxVSF+FABJADveWkH6oAAAAAElFTkSuQmCC';

await runScript('j5-photo-draft', 'Photo draft: upload, inline preview, download 404, hard delete', async (j) => {
  const patient = j.scaffold.patient;
  // FilePond needs a real image file; it lives in the run's evidence dir so the
  // repository stays free of binary fixtures.
  const fixture = evidencePath('fixtures', 'verify-photo.png');
  if (!fs.existsSync(fixture)) {
    fs.writeFileSync(fixture, Buffer.from(PNG_BASE64, 'base64'));
  }

  let photoUrl = '';
  let storedFile = '';

  await j.step('student uploads a photo through FilePond', async () => {
    const page = await j.open('student', STUDENT_EMAIL);
    const response = await page.goto(`/mediafiles/photos/create/${patient.id}/`);
    j.assert(response.status() === 200, `photo create page not reachable: ${response.status()}`);
    await page.locator('.filepond--root').waitFor({ timeout: 15000 });
    await page.locator('input[name="filepond"]').setInputFiles(fixture);
    await page.waitForFunction(
      () => document.querySelector('input[name="upload_id"]')?.value?.length > 0,
      undefined,
      { timeout: 20000 },
    );
    const uploadId = await page.locator('input[name="upload_id"]').inputValue();
    await page.fill('input[name="description"]', 'Foto de verificacao automatizada');
    await page.fill('input[name="caption"]', 'Legenda da verificacao');
    await Promise.all([page.waitForNavigation(), page.click('button[type=submit]')]);
    await page.waitForURL(`**${patient.timeline_path}`);
    j.assert((await page.locator('.draft-badge').count()) === 1, 'photo draft badge missing');
    await j.shot(page, 'timeline-photo-draft');
    return [`upload_id=${uploadId}`];
  });

  await j.step('draft photo is viewable inline but not downloadable', async () => {
    const page = j.page('student');
    const link = page.locator('article.timeline-card a[href*="/mediafiles/photos/"]').first();
    photoUrl = (await link.getAttribute('href')) ?? '';
    await page.goto(photoUrl);
    const rendered = await page.locator('.card-body img').first().evaluate((img) => ({
      complete: img.complete,
      width: img.naturalWidth,
      src: img.getAttribute('src'),
    }));
    j.assert(rendered.complete && rendered.width > 0, `inline image not rendered: ${JSON.stringify(rendered)}`);
    const downloadHref = await page.locator('a[href*="/download/"]').first().getAttribute('href');
    const download = await page.request.get(downloadHref);
    j.assert(download.status() === 404, `draft download must be 404, got ${download.status()}`);
    await j.shot(page, 'photo-detail-inline');
    return [`detail=${photoUrl}`, `inline image ${rendered.width}px`, `GET ${downloadHref} -> 404`];
  });

  await j.step('storage holds the uploaded file while the draft exists', async () => {
    const db = probePatient('before-j5-delete', patient.id);
    const photos = db.photos ?? [];
    j.assert(photos.length === 1, `expected one photo row, got ${photos.length}`);
    j.assert(photos[0].is_draft === true, 'photo row is not a draft');
    j.assert(photos[0].stored_files.length === 1, `expected one stored file, got ${JSON.stringify(photos[0].stored_files)}`);
    storedFile = photos[0].stored_files[0];
    return [`file_id=${photos[0].file_id}`, `stored=${storedFile}`];
  });

  await j.step('hard delete removes the row and the stored file', async () => {
    const page = j.page('student');
    await page.goto(photoUrl);
    await page.click('a[href*="/mediafiles/photos/"][href$="/delete/"]');
    await page.waitForURL('**/mediafiles/photos/*/delete/');
    await page.check('#confirmDelete');
    await Promise.all([page.waitForNavigation(), page.click('#deleteBtn')]);
    await page.waitForURL(`**${patient.timeline_path}`);
    j.assert((await page.locator('article.timeline-card').count()) === 0, 'photo card still on timeline after delete');
    const detail = await page.goto(photoUrl);
    j.assert(detail.status() === 404, `deleted photo detail should 404, got ${detail.status()}`);

    const db = probePatient('after-j5-delete', patient.id, { filePath: storedFile });
    j.assert((db.photos ?? []).length === 0, 'photo row survived hard delete');
    j.assert(db.probe_file?.exists === false, `stored file still on disk: ${storedFile}`);
    return ['timeline empty', `GET ${photoUrl} -> 404`, 'photos=0 rows', `file gone: ${storedFile}`];
  });
});

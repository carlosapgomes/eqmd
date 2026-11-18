# Design: Editor-owned searchable classification

## D1. Baseline and accepted user outcome

The operator cannot clear the final selected tag in update or add a second tag
in create with ordinary clicks. The diagnostic confirms the native multiple
select requires modifiers, while actual authorized browser POSTs correctly
create, replace and clear editable associations.

Evidence: /tmp/eqmd-report-template-editor-audit/report.md, nine Chrome groups,
49 existing tests and exact-owner rollback. These are diagnosis, not GREEN
proof for the new interaction. Core findings are repeated here so execution
does not depend on ephemeral files.

The operator approved searchable multiple selection and removable chips in both
editors. Zero classification is valid. Changes are persisted only by the normal
Criar/Salvar Modelo submit, not by an editor-specific Apply.

## D2. Reuse authority, not the discovery transport

ReportTemplateForm already renders editor_tag_choices: active assignable rows
plus existing readable/removable historical associations. Filtering uses the
broader requester-readable boundary. Shared tag-selector.js also owns repeated
tags, manual/default markers and preference integration, which are wrong here.

Use a small editor-owned progressive enhancement. Its complete option universe
is the existing form.tag_ids native options. It cannot fetch or manufacture more
identities. Search is local case/accent-insensitive label substring matching,
including the labels/team/lifecycle text already supplied by the server.
Preserve original display text and server ordering.

Do not add a lookup endpoint, permission, controller adapter, forms.py branch
or generic-selector configuration framework. Do not copy the large discovery
controller. The existing read-only services remain the authority.

## D3. One field remains the submission source of truth

Keep the original enabled, named multiple select tag_ids and the existing
tags_present=1 marker. After successful initialization, hide the native
presentation and mirror every enhanced choice into option.selected.
The hidden native select still participates in ordinary form submission.

Do not disable it, remove its name or add a second set of named tag_ids inputs.
Zero selected options contributes no tag_ids value; tags_present=1 makes that
an explicit authorized clear. Marker omission retains existing legacy behavior.
No tags, tag_mode, tag_filter or discovery/preference marker belongs here.

Seed from actual rendered selected options, not field.initial or stored model
tags. A bound invalid form may differ from the saved instance. Unauthorized
posted IDs are never reconstructed as client choices, labels or chips.

Search and chip actions never submit, fetch, navigate, push history or write
browser storage. Every generated button has type=button. Enter in the search
field is handled without submitting the parent form. Other form fields are
neither read nor written by this module.

## D4. Shared form presentation

Replace only the existing Tags block in reporttemplate_form.html with
components/\_report_template_tag_editor.html. Keep its field errors and optional
classification guidance, and leave the outer CSRF/form/submit controls intact.
Load only js/report-template-tag-editor.js through versioned_static, deferred
on these two pages.

The partial provides:

- Native label/select and desktop Ctrl/Cmd selection/removal guidance.
- Initially hidden enhanced label/search, in-flow bounded/scrollable results,
  selected chips and a polite status region.
- Ordinary click/tap adds an offered unselected tag without replacing others.
  Already selected results are visibly marked and inert; chip removal is explicit.
- Each chip has Remover <display label> da seleção, with a visual × and no
  catalogue-edit/delete meaning.
- Empty selection says Nenhuma tag selecionada. This describes this field,
  not a claim that hidden/protected database links do not exist.
- No-choice/no-match guidance is generic and does not disclose hidden links
  or their counts. Do not offer creation of a new catalogue row.

Render labels with Django escaping and DOM textContent/createElement, never
raw HTML from options/search input. Use existing neutral chip/removal classes
and Bootstrap utilities. Keep results in normal flow, not a new overlay.
No shared CSS change is planned; long names must wrap inside the field.

Initialize atomically: build the initial state and attach handlers before
hiding native controls/exposing enhanced ones. Failure or blocked assets must
not leave both interfaces hidden. Native and enhanced labels target the
appropriate currently visible controls; there is no orphaned label/focus stop.
Enhancement is idempotent and listens only inside its own editor root.

## D5. Keyboard and fallback

Support tab navigation, ordinary Enter/Space activation on result/removal
buttons, and search Enter without parent submission. Escape collapses results
without changing selected tags or other fields; focused removal has a sensible
next-chip/search focus destination after its chip disappears.

Use the existing chip target sizing: minimum 24x24 CSS px and 44x44 on coarse
pointers. Prove 1440/390/320px and long labels against the same baseline shell.

Without JavaScript, or when the new asset cannot load, the original multiple
select remains enabled and visible. State the Ctrl/Cmd desktop guidance:
the no-modifier outcome is the enhanced default, not a new no-JS widget promise.
No-JS still supports multiple values, last-selection removal and explicit empty
POST using the existing marker. If native form reset occurs, enhanced display
must resync from the actual native selection after reset without touching text.

## D6. Permission, historical and validation boundaries

Do not expose a tag merely because discovery can read it. Keep current model
ownership/admin checks and per-tag assignment/removal rules. Staff is not a
catalogue-policy override. No automatic specialty tags are inserted into create.

Existing inactive/archived offered selections retain their state labels and may
be removed or reselected before saving: until removal is saved, that is retention
of the existing association, not a new historical assignment. After successful
removal, a subsequent editor GET must no longer offer it as a new choice.
Hidden or non-removable associations remain outside controls and survive saves.

POST continues through the existing atomic association service and history.
Revoked/forged/inactive new identities fail generically with no partial fields,
M2M or audit save. Other validation errors retain authorized submitted selections,
including explicit empty, plus name/markdown/switches. Retrying remains possible.
No raw rejected identity or protected metadata is rendered through the component.

## D7. Small scope, build and rollback

One vertical slice delivers the complete create/update interaction and its POST
proof. Existing classification backend, report/discovery controllers and prior
RTFA assets stay read-only. New modules remain below 300 lines, helpers <=40.
Any required expansion or new architecture/persistence decision stops execution.

Add only the new editor source-to-static copy entry to webpack.config.js.
Build with existing npm tooling and use the existing content-versioned URL.
Generated output is build output, never hand-edited. No install or service
lifecycle operation is required.

Rollback restores the Tags-block include/asset reference and matching build.
There is no schema or data rollback. Do not undo the unrelated accepted RTFA
working-tree changes. The active RTFA delta modifies different reports
requirements; this plan neither syncs nor closes that change.

// DailyNote card copy flow: direct copy up to one field, dialog above it.
// The dialog DOM is built on first use (design D4) and reset on every open.

import chunks from './dailynote-chunks.js';
import {
    copyTextToClipboard,
    showClipboardFeedback,
    showToast,
} from './clipboard-utils.js';

const {
    HOSPITAL_FIELD_LIMIT,
    MAX_PART_BUTTONS,
    shouldOpenCopyDialog,
    splitDailyNoteIntoParts,
} = chunks;

const DIALOG_TITLE_ID = 'dailynoteCopyDialogTitle';
const DIALOG_TITLE = 'Copiar evolução';
const DIALOG_INTRO = 'Cada campo do sistema hospitalar aceita até 4.000 caracteres.';
const EMPTY_CONTENT_MESSAGE = 'Nenhum conteúdo para copiar';
const COPY_FAILURE_MESSAGE = 'Falha ao copiar conteúdo';
const COPIED_MESSAGE = 'Conteúdo copiado para a área de transferência!';
const HOSPITAL_CAPACITY = MAX_PART_BUTTONS * HOSPITAL_FIELD_LIMIT;

let dialogShell = null;

export function initDailyNoteCopy() {
    document.addEventListener('click', handleCopyClick);
}

function handleCopyClick(event) {
    const button = event.target.closest('.copy-dailynote-btn');
    if (!button) {
        return;
    }
    event.preventDefault();
    startCopyFromButton(button);
}

function startCopyFromButton(button) {
    const raw = button.dataset.content || '';
    if (!raw.trim()) {
        showToast(EMPTY_CONTENT_MESSAGE, 'danger');
        return;
    }
    if (shouldOpenCopyDialog(raw)) {
        openCopyDialog(raw);
        return;
    }
    copyDirectly(button, raw);
}

async function copyDirectly(button, content) {
    try {
        await copyTextToClipboard(content);
        showClipboardFeedback(button, true);
    } catch (error) {
        console.error('Failed to copy text:', error);
        showClipboardFeedback(button, false, COPY_FAILURE_MESSAGE);
    }
}

function openCopyDialog(raw) {
    const split = splitDailyNoteIntoParts(raw);
    if (split.parts.length === 0) {
        showToast(EMPTY_CONTENT_MESSAGE, 'danger');
        return;
    }
    const shell = ensureDialogShell();
    renderDialog(shell, raw, split);
    shell.modal.show();
}

function renderDialog(shell, raw, split) {
    renderFullCopyButton(shell.fullCopyContainer, raw, split.totalLength);
    renderPartButtons(shell.partsContainer, split.parts);
    renderUncoveredWarning(shell.warningContainer, split);
}

function ensureDialogShell() {
    if (!dialogShell) {
        dialogShell = buildDialogElement();
        document.body.appendChild(dialogShell.element);
    }
    return dialogShell;
}

function buildDialogElement() {
    const element = createElement('div', 'modal fade');
    element.tabIndex = -1;
    element.setAttribute('aria-labelledby', DIALOG_TITLE_ID);
    element.setAttribute('aria-hidden', 'true');

    const body = buildDialogBody();
    const dialog = createElement('div', 'modal-dialog modal-dialog-scrollable');
    const content = createElement('div', 'modal-content');
    content.append(createDialogHeader(), body.container, createDialogFooter());
    dialog.appendChild(content);
    element.appendChild(dialog);

    return {
        element,
        modal: new window.bootstrap.Modal(element),
        fullCopyContainer: body.fullCopyContainer,
        partsContainer: body.partsContainer,
        warningContainer: body.warningContainer,
    };
}

function buildDialogBody() {
    const container = createElement('div', 'modal-body');
    const intro = createElement('p', 'text-muted small');
    intro.textContent = DIALOG_INTRO;
    const warningContainer = createElement('div', 'alert alert-warning mt-3 d-none');
    warningContainer.setAttribute('role', 'status');
    const fullCopyContainer = createElement('div', 'd-grid gap-2');
    const partsContainer = createElement('div', 'd-grid gap-2 mt-2');
    container.append(intro, warningContainer, fullCopyContainer, partsContainer);
    return { container, warningContainer, fullCopyContainer, partsContainer };
}

function createDialogHeader() {
    const header = createElement('div', 'modal-header');
    const title = createElement('h2', 'modal-title fs-5');
    title.id = DIALOG_TITLE_ID;
    title.textContent = DIALOG_TITLE;
    const closeButton = createDismissButton('btn-close');
    closeButton.setAttribute('aria-label', 'Fechar');
    header.append(title, closeButton);
    return header;
}

function createDialogFooter() {
    const footer = createElement('div', 'modal-footer');
    const closeButton = createDismissButton('btn btn-secondary');
    closeButton.textContent = 'Fechar';
    footer.appendChild(closeButton);
    return footer;
}

function createDismissButton(className) {
    const button = createElement('button', className);
    button.type = 'button';
    button.dataset.bsDismiss = 'modal';
    return button;
}

function renderFullCopyButton(container, raw, totalLength) {
    const count = formatCount(totalLength);
    const button = createCopyButton({
        className: 'btn btn-primary',
        label: `Copiar tudo (${count} caracteres)`,
        ariaLabel: `Copiar a evolução completa (${count} caracteres)`,
    });
    button.addEventListener('click', () => copyIntoButton(button, raw));
    container.replaceChildren(button);
}

function renderPartButtons(container, parts) {
    const buttons = parts
        .slice(0, MAX_PART_BUTTONS)
        .map((part, index) => createPartButton(part, index));
    container.replaceChildren(...buttons);
}

function createPartButton(part, index) {
    const number = index + 1;
    const count = formatCount(part.text.length);
    const button = createCopyButton({
        className: 'btn btn-outline-primary text-start',
        label: `P${number} · ${count}/${formatCount(HOSPITAL_FIELD_LIMIT)}`,
        ariaLabel: `Copiar parte ${number} da evolução (${count} caracteres)`,
    });
    button.addEventListener('click', () => copyIntoButton(button, part.text));
    return button;
}

function createCopyButton({ className, label, ariaLabel }) {
    const button = createElement('button', className);
    button.type = 'button';
    button.setAttribute('aria-label', ariaLabel);
    button.textContent = label;
    return button;
}

async function copyIntoButton(button, text) {
    try {
        await copyTextToClipboard(text);
        markCopied(button);
        showToast(COPIED_MESSAGE, 'success');
    } catch (error) {
        console.error('Failed to copy text:', error);
        showToast(COPY_FAILURE_MESSAGE, 'danger');
    }
}

function markCopied(button) {
    if (button.dataset.copied === 'true') {
        return;
    }
    button.dataset.copied = 'true';
    button.classList.remove('btn-primary', 'btn-outline-primary');
    button.classList.add('btn-success');
    const indicator = createElement('i', 'bi bi-check ms-1');
    indicator.setAttribute('aria-hidden', 'true');
    button.appendChild(indicator);
}

function renderUncoveredWarning(container, split) {
    if (split.uncoveredLength <= 0) {
        container.textContent = '';
        container.classList.add('d-none');
        return;
    }
    container.textContent = uncoveredWarningText(split);
    container.classList.remove('d-none');
}

function uncoveredWarningText(split) {
    const message =
        `O conteúdo tem ${formatCount(split.totalLength)} caracteres, mas os ` +
        `${MAX_PART_BUTTONS} primeiros campos exibidos cobrem ` +
        `${formatCount(split.coveredLength)} caracteres. Use "Copiar tudo" ` +
        'para copiar o conteúdo completo.';
    if (split.totalLength <= HOSPITAL_CAPACITY) {
        return message;
    }
    return (
        `${message} O sistema hospitalar aceita ${MAX_PART_BUTTONS} campos de ` +
        `${formatCount(HOSPITAL_FIELD_LIMIT)} caracteres, ` +
        `${formatCount(HOSPITAL_CAPACITY)} no total.`
    );
}

function createElement(tagName, className) {
    const element = document.createElement(tagName);
    element.className = className;
    return element;
}

function formatCount(value) {
    return value.toLocaleString('pt-BR');
}

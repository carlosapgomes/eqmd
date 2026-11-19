/**
 * Pure DailyNote splitting for the hospital copy dialog (design D5-D8).
 *
 * CommonJS on purpose: the Node harness loads this file without a bundler,
 * while webpack consumes it through its default-export interop.
 */

const HOSPITAL_FIELD_LIMIT = 4000;
const PART_TARGET = 3900;
const MAX_PART_BUTTONS = 4;

const PARAGRAPH_SEPARATOR = "\n\n";
const LINE_SEPARATOR = "\n";
const SENTENCE_SEPARATOR = " ";
const NO_SEPARATOR = "";
const PARAGRAPH_BREAK = /\n{2,}/;
const SENTENCE_BOUNDARY = /(?<=[.!?…])\s+/;

function shouldOpenCopyDialog(raw) {
    return raw.length > HOSPITAL_FIELD_LIMIT;
}

function splitDailyNoteIntoParts(raw) {
    const normalized = raw.replace(/\r\n/g, LINE_SEPARATOR).trim();
    if (!normalized) {
        return emptySplit();
    }
    const parts = packUnitsIntoParts(buildUnits(normalized));
    const coveredLength = measureCoveredLength(parts);
    return {
        parts,
        totalLength: normalized.length,
        coveredLength,
        uncoveredLength: normalized.length - coveredLength,
    };
}

function emptySplit() {
    return { parts: [], totalLength: 0, coveredLength: 0, uncoveredLength: 0 };
}

function buildUnits(normalized) {
    const units = [];
    for (const block of normalized.split(PARAGRAPH_BREAK)) {
        units.push(...splitBlockIntoUnits(block, PARAGRAPH_SEPARATOR));
    }
    return units;
}

function splitBlockIntoUnits(block, separator) {
    if (block.length <= HOSPITAL_FIELD_LIMIT) {
        return [{ text: block, sep: separator }];
    }
    const units = [];
    block.split(LINE_SEPARATOR).forEach((line, index) => {
        const lineSeparator = index === 0 ? separator : LINE_SEPARATOR;
        units.push(...splitLineIntoUnits(line, lineSeparator));
    });
    return units;
}

function splitLineIntoUnits(line, separator) {
    if (line.length <= HOSPITAL_FIELD_LIMIT) {
        return [{ text: line, sep: separator }];
    }
    const units = [];
    line.split(SENTENCE_BOUNDARY).forEach((sentence, index) => {
        const sentenceSeparator = index === 0 ? separator : SENTENCE_SEPARATOR;
        units.push(...splitSentenceIntoUnits(sentence, sentenceSeparator));
    });
    return units;
}

function splitSentenceIntoUnits(sentence, separator) {
    if (sentence.length <= HOSPITAL_FIELD_LIMIT) {
        return [{ text: sentence, sep: separator }];
    }
    const units = [];
    for (let start = 0; start < sentence.length; start += HOSPITAL_FIELD_LIMIT) {
        const isFirstPiece = start === 0;
        units.push({
            text: sentence.slice(start, start + HOSPITAL_FIELD_LIMIT),
            sep: isFirstPiece ? separator : NO_SEPARATOR,
        });
    }
    return units;
}

function packUnitsIntoParts(units) {
    const parts = [];
    let openPart = null;
    for (const unit of units) {
        if (!openPart) {
            openPart = createPart(unit.text);
            continue;
        }
        const joinedLength =
            openPart.text.length + unit.sep.length + unit.text.length;
        if (joinedLength <= PART_TARGET) {
            openPart.text += unit.sep + unit.text;
            continue;
        }
        openPart.separatorToNextPart = unit.sep;
        parts.push(openPart);
        openPart = createPart(unit.text);
    }
    if (openPart) {
        parts.push(openPart);
    }
    return parts;
}

function createPart(text) {
    return { text, separatorToNextPart: NO_SEPARATOR };
}

function measureCoveredLength(parts) {
    const shownParts = parts.slice(0, MAX_PART_BUTTONS);
    let coveredLength = shownParts.reduce((length, part) => {
        return length + part.text.length;
    }, 0);
    for (let index = 0; index < shownParts.length - 1; index += 1) {
        coveredLength += shownParts[index].separatorToNextPart.length;
    }
    return coveredLength;
}

module.exports = {
    HOSPITAL_FIELD_LIMIT,
    PART_TARGET,
    MAX_PART_BUTTONS,
    shouldOpenCopyDialog,
    splitDailyNoteIntoParts,
};

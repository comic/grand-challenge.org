document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    // Added a fallback for empty highlight param to prevent errors
    const highlightText = normalizeText(params.get("highlight") || "");
    if (!highlightText) return;

    const content = document.getElementById("pageContainer");
    if (!content) return;

    // IMPORTANT: This whitespace normalization is the source of complexity.
    // The traversal logic must perfectly match this.
    const normalizedInnerText = normalizeText(content.innerText);
    const startIndex = normalizedInnerText.indexOf(highlightText);

    if (startIndex === -1) {
        console.warn(`Highlight text not found: "${highlightText}"`);
        return;
    }
    const endIndex = startIndex + highlightText.length;

    highlightRangeAndScroll(startIndex, endIndex, content);
});

function normalizeText(text) {
    return text
        .replace(/¶/g, "")
        .replace(/\s+/g, " ")
        .trimStart()
        .toLowerCase();
}

/**
 * Determine whether a node's text content is entirely whitespace.
 * @param {Node} node A node implementing the `CharacterData` interface
 * @return            `true` if all of the text content of `node` is whitespace.
 */
function isAllWhitespace(node) {
    return !/[^\t\n\r ]/.test(node.textContent);
}

/**
 * Wraps a TEXT_NODE with a <mark> element.
 * @param {Node} node The text node to wrap.
 * @returns {HTMLElement} The created <mark> element.
 */
function wrapTextNode(node) {
    const mark = document.createElement("mark");
    node.parentNode.insertBefore(mark, node);
    mark.appendChild(node);
    return mark;
}

/**
 * Highlights a range and scrolls the first highlighted element into view.
 */
function highlightRangeAndScroll(startIndex, endIndex, rootElement) {
    if (startIndex < 0 || endIndex < startIndex) {
        return;
    }

    const context = {
        currentSequenceText: "",
        characterCount: 0,
        highlighting: false,
        firstNode: null,
    };

    traverseAndHighlight(rootElement, startIndex, endIndex, context);

    if (context.firstNode) {
        // scrollIntoView works on elements, so if firstNode is a text node,
        // we use its parentElement.
        const scrollTarget =
            context.firstNode.nodeType === Node.TEXT_NODE
                ? context.firstNode.parentElement
                : context.firstNode;

        scrollTarget.scrollIntoView({
            behavior: "smooth",
            block: "center",
        });
    }
}

// List of tags that should be wrapped entirely, not split.
const ATOMIC_NODES = ["STRONG", "B", "EM", "I", "MARK", "SPAN", "A"];

/**
 * Recursively traverses the DOM and highlights text based on character indices.
 */
function traverseAndHighlight(node, startIndex, endIndex, context) {
    if (context.characterCount >= endIndex) {
        return;
    }
    if (node.nodeType === Node.ELEMENT_NODE) {
        // Check if the current element is one we should wrap whole.
        if (ATOMIC_NODES.includes(node.tagName)) {
            context.currentSequenceText = normalizeText(
                `${context.currentSequenceText}${node.textContent}`,
            );
            context.characterCount = context.currentSequenceText.length;
            const endOfNode = context.characterCount;

            // Check if this node's text content falls within the highlight range
            const shouldHighlight =
                context.highlighting || // Already highlighting
                endOfNode > startIndex; // Highlighting should start

            if (shouldHighlight) {
                // If this is the very first thing we highlight, store it for scrolling
                if (!context.firstNode) {
                    context.firstNode = node;
                }
                node.classList.add("mark"); // Add a class for styling
                context.highlighting = true; // Ensure we stay in highlighting mode
            }

            // DO NOT traverse children.
            // We've treated this element as an atomic unit.
            return;
        }

        for (const child of Array.from(node.childNodes)) {
            traverseAndHighlight(child, startIndex, endIndex, context);
        }
        return;
    }

    if (node.nodeType === Node.TEXT_NODE) {
        context.currentSequenceText = normalizeText(
            `${context.currentSequenceText}${node.textContent}`,
        );
        const startOfNode = context.characterCount;
        context.characterCount = context.currentSequenceText.length;
        const endOfNode = context.characterCount;

        // If this node is completely outside the range, do nothing.
        if (endOfNode <= startIndex || startOfNode >= endIndex) {
            return;
        }

        // If this node is completely whitespace, do nothing.
        if (isAllWhitespace(node)) {
            return;
        }

        // Determine if we are starting, ending, or fully inside the highlight
        const shouldStart = startOfNode <= startIndex;
        const shouldEnd = endOfNode >= endIndex;

        // The node contains the entire highlight
        if (shouldStart && shouldEnd) {
            const startOffset = startIndex - startOfNode;
            const endOffset = endIndex - startOfNode;
            const middleBit = node.splitText(startOffset);
            middleBit.splitText(endOffset - startOffset);
            context.firstNode = wrapTextNode(middleBit);
        }
        // The node contains the start of the highlight
        else if (shouldStart) {
            const startOffset = startIndex - startOfNode;
            const nodeToWrap = node.splitText(startOffset);
            context.firstNode = wrapTextNode(nodeToWrap);
            context.highlighting = true;
        }
        // The node contains the end of the highlight
        else if (shouldEnd) {
            const endOffset = endIndex - startOfNode;
            node.splitText(endOffset);
            wrapTextNode(node);
        }
        // The node is fully contained within the highlight
        else if (context.highlighting) {
            wrapTextNode(node);
        }
    }
}

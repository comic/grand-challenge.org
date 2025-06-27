document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    // Added a fallback for empty highlight param to prevent errors
    const highlightText = (params.get("highlight") || "").replace(/\s+/g, " ");
    if (!highlightText) return;

    const content = document.getElementById("pageContainer");
    if (!content) return;

    // IMPORTANT: This whitespace normalization is the source of complexity.
    // The traversal logic must perfectly match this.
    const normalizedInnerText = content.innerText.replace(/\s+/g, " ");
    const startIndex = normalizedInnerText.indexOf(highlightText);

    if (startIndex === -1) {
        console.warn(`Highlight text not found: "${highlightText}"`);
        return;
    }
    const endIndex = startIndex + highlightText.length;

    highlightRangeAndScroll(startIndex, endIndex, content);
});

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
        characterCount: 0,
        first_node: null,
    };

    traverseAndHighlight(rootElement, startIndex, endIndex, context);

    if (context.first_node) {
        context.first_node.scrollIntoView({
            behavior: "smooth",
            block: "center",
        });
    }
}

// List of element tags that should be treated as a single, indivisible unit for highlighting.
const ATOMIC_NODES = ["STRONG", "B", "EM", "I", "MARK", "SPAN", "A"];

/**
 * Recursively traverses the DOM, highlighting full nodes that fall within a
 * character range.
 */
function traverseAndHighlight(node, startIndex, endIndex, context) {
    if (context.characterCount > endIndex) {
        return;
    }

    const isAtomic =
        node.nodeType === Node.TEXT_NODE ||
        (node.nodeType === Node.ELEMENT_NODE &&
            ATOMIC_NODES.includes(node.tagName));

    if (isAtomic) {
        // Calculate the normalized length and character range of this atomic node.
        // This normalization MUST match the one used to find startIndex/endIndex.
        const nodeText = node.textContent.replace(/\s+/g, " ");
        const nodeLength = nodeText.length;
        const startOfNode = context.characterCount;
        const endOfNode = startOfNode + nodeLength;

        context.characterCount = endOfNode;

        if (startOfNode < endIndex && endOfNode > startIndex) {
            let highlightedElement;
            if (node.nodeType === Node.TEXT_NODE) {
                highlightedElement = wrapTextNode(node);
            } else {
                node.classList.add("mark");
                highlightedElement = node;
            }

            if (!context.first_node) {
                context.first_node = highlightedElement;
            }
        }
    } else if (node.nodeType === Node.ELEMENT_NODE) {
        for (const child of Array.from(node.childNodes)) {
            traverseAndHighlight(child, startIndex, endIndex, context);
        }
    }
}

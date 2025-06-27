document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    const highlightText = params.get("highlight");
    if (!highlightText || highlightText.trim() === "") return;

    const content = document.getElementById("pageContainer");
    if (!content) return;

    // The new function directly finds, highlights, and returns the first element.
    const firstHighlightedElement = findAndHighlightSequence(
        content,
        highlightText,
    );

    if (firstHighlightedElement) {
        // If a match was found and highlighted, scroll it into view.
        firstHighlightedElement.scrollIntoView({
            behavior: "smooth",
            block: "center",
        });
    } else {
        console.warn(`Highlight text not found: "${highlightText}"`);
    }
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

// List of element tags that should be treated as a single, indivisible unit for highlighting.
const ATOMIC_NODES = ["STRONG", "B", "EM", "I", "MARK", "SPAN", "A"];

/**
 * Recursively traverses the DOM to collect all "atomic" nodes (text nodes and
 * specific inline elements) into a flat list, preserving their document order.
 * @param {Node} node The starting node for traversal.
 * @param {Array<Node>} nodes The accumulator array for collected nodes.
 * @returns {Array<Node>} The flat list of atomic nodes.
 */
function collectAtomicNodes(node, nodes = []) {
    const isAtomic =
        node.nodeType === Node.TEXT_NODE ||
        (node.nodeType === Node.ELEMENT_NODE &&
            ATOMIC_NODES.includes(node.tagName));

    if (isAtomic) {
        // Only add non-empty text nodes
        if (
            node.nodeType !== Node.TEXT_NODE ||
            node.textContent.trim() !== ""
        ) {
            nodes.push(node);
        }
    } else if (node.nodeType === Node.ELEMENT_NODE) {
        for (const child of Array.from(node.childNodes)) {
            collectAtomicNodes(child, nodes);
        }
    }
    return nodes;
}

/**
 * Finds a sequence of nodes that match the search text and highlights them.
 * This approach avoids the fragility of index-based highlighting by matching
 * against the text content of the nodes directly.
 * @param {HTMLElement} rootElement The element to search within.
 * @param {string} searchText The text to find.
 * @returns {HTMLElement|null} The first highlighted element, or null if not found.
 */
function findAndHighlightSequence(rootElement, searchText) {
    const nodes = collectAtomicNodes(rootElement);
    const normalizedSearchText = searchText
        .replace(/\s+/g, " ")
        .trim()
        .toLowerCase();

    let currentSequenceText = "";
    const charCountNodes = [];
    let startIndex = -1;
    for (let i = 0; i < nodes.length; i++) {
        currentSequenceText += ` ${nodes[i].textContent}`;
        const normalizedCurrentText = currentSequenceText
            .replace(/¶/g, "")
            .replace(/\s+/g, " ")
            .trim()
            .toLowerCase();
        charCountNodes.push(normalizedCurrentText.length);

        startIndex = normalizedCurrentText.indexOf(normalizedSearchText);

        if (startIndex !== -1) {
            const firstNode = charCountNodes.findIndex(
                charCount => charCount > startIndex,
            );
            // Match found for the sequence of nodes from i to j.
            const nodesToHighlight = nodes.slice(firstNode, i + 1);
            let firstHighlightedElement = null;
            for (const node of nodesToHighlight) {
                let highlightedElement;
                if (node.nodeType === Node.TEXT_NODE) {
                    highlightedElement = wrapTextNode(node);
                } else {
                    node.classList.add("mark");
                    highlightedElement = node;
                }
                if (!firstHighlightedElement) {
                    firstHighlightedElement = highlightedElement;
                }
            }
            return firstHighlightedElement;
        }
    }
    return null;
}

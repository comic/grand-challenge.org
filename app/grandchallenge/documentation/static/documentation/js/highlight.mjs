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
        highlighting: false,
        first_node: null,
    };

    traverseAndHighlight(rootElement, startIndex, endIndex, context);

    if (context.first_node) {
        // scrollIntoView works on elements, so if first_node is a text node,
        // we use its parentElement.
        const scrollTarget =
            context.first_node.nodeType === Node.TEXT_NODE
                ? context.first_node.parentElement
                : context.first_node;

        scrollTarget.scrollIntoView({
            behavior: "smooth",
            block: "center",
        });
    }
}

// List of tags that should be wrapped entirely, not split.
const FULL_HIGHLIGHT_NODES = ["STRONG", "B", "EM", "I", "MARK", "SPAN", "A"];

/**
 * Recursively traverses the DOM and highlights text based on character indices.
 */
function traverseAndHighlight(node, startIndex, endIndex, context) {
    if (context.characterCount >= endIndex || context.done) {
        return;
    }

    if (node.nodeType === Node.ELEMENT_NODE) {
        // Check if the current element is one we should wrap whole.
        if (FULL_HIGHLIGHT_NODES.includes(node.tagName)) {
            const nodeText = node.textContent.replace(/\s+/g, " ");
            const nodeLength = nodeText.length;
            const startOfNode = context.characterCount;
            const endOfNode = startOfNode + nodeLength;

            // Check if this node's text content falls within the highlight range
            const shouldHighlight =
                (context.highlighting && endOfNode <= endIndex) || // Already highlighting and this node is fully contained
                (startOfNode < endIndex && endOfNode > startIndex); // Node overlaps with the highlight range

            if (shouldHighlight) {
                // If this is the very first thing we highlight, store it for scrolling
                if (!context.first_node) {
                    context.first_node = node;
                }
                // wrapElementNode(node); // Wrap the entire element
                node.classList.add("mark"); // Add a class for styling (or wrap the element as desired)
                context.highlighting = true; // Ensure we stay in highlighting mode
            }

            // Update character count and, crucially, DO NOT traverse children.
            // We've treated this element as an atomic unit.
            context.characterCount = endOfNode;
            return;
        }

        for (const child of Array.from(node.childNodes)) {
            traverseAndHighlight(child, startIndex, endIndex, context);
        }
        return;
    }

    if (node.nodeType === Node.TEXT_NODE) {
        // Your whitespace handling is complex. For simplicity in this example,
        // we'll use a more direct textContent length, but your logic
        // for collapsing whitespace would go here. To correctly align with `normalizedInnerText`,
        // the length of the text node's content must also be normalized.
        const nodeLength = node.textContent.replace(/\s+/g, " ").length;
        const startOfNode = context.characterCount;
        const endOfNode = startOfNode + nodeLength;

        // This must be updated AFTER we use startOfNode
        context.characterCount = endOfNode;

        // If this node is completely outside the range, do nothing.
        if (endOfNode <= startIndex || startOfNode >= endIndex) {
            return;
        }

        // Determine if we are starting, ending, or fully inside the highlight
        const shouldStart = startOfNode <= startIndex && endOfNode > startIndex;
        const shouldEnd = startOfNode < endIndex && endOfNode >= endIndex;

        // The node contains the entire highlight
        if (shouldStart && shouldEnd) {
            const startOffset = startIndex - startOfNode;
            const endOffset = endIndex - startOfNode;
            const middleBit = node.splitText(startOffset);
            middleBit.splitText(endOffset - startOffset);
            context.first_node = wrapTextNode(middleBit);
            context.done = true;
        }
        // The node contains the start of the highlight
        else if (shouldStart) {
            const startOffset = startIndex - startOfNode;
            const nodeToWrap = node.splitText(startOffset);
            context.first_node = wrapTextNode(nodeToWrap);
            context.highlighting = true;
        }
        // The node contains the end of the highlight
        else if (shouldEnd) {
            const endOffset = endIndex - startOfNode;
            node.splitText(endOffset);
            wrapTextNode(node);
            context.highlighting = false;
            context.done = true;
        }
        // The node is fully contained within the highlight
        else if (context.highlighting) {
            wrapTextNode(node);
        }
    }
}

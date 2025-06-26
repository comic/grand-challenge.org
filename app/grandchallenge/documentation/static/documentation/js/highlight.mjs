document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    const highlightText = params.get("highlight").replace(/\s+/g, " ");
    if (!highlightText) return;

    const content = document.getElementById("pageContainer");
    if (!content) return;

    const startIndex = content.innerText
        .replace(/\s+/g, " ")
        .indexOf(highlightText);
    if (startIndex === -1) {
        return;
    }
    const endIndex = startIndex + highlightText.length;

    highlightRangeAndScroll(startIndex, endIndex, content);
});

/**
 * Wraps a DOM Node with a <mark> element.
 * @param {Node} node The text node to wrap.
 * @returns {HTMLElement} The created <mark> element.
 */
function wrapNode(node) {
    const mark = document.createElement("mark");
    node.parentNode.insertBefore(mark, node);
    mark.appendChild(node);
    return mark;
}

/**
 * Highlights a range of text across multiple elements within a root container.
 *
 * @param {number} startIndex The starting character index of the selection.
 * @param {number} endIndex The ending character index of the selection.
 * @param {HTMLElement} rootElement The container element in which to perform the highlight.
 */
function highlightRangeAndScroll(startIndex, endIndex, rootElement) {
    if (startIndex < 0 || endIndex < startIndex) {
        return;
    }

    // This object will be passed by reference through the recursive calls
    const context = {
        characterCount: 0,
        highlighting: false, // Are we currently in a state of highlighting?
        skipping_whitespace: false,
        first_node: null,
    };

    // Start the traversal
    traverseAndHighlight(rootElement, startIndex, endIndex, context);

    if (context.first_node) {
        context.first_node.parentElement.scrollIntoView({
            behavior: "smooth",
            block: "center",
        });
    }
}

/**
 * Determine whether a node's text content is entirely whitespace.
 *
 * @param {Node} node A node implementing the `CharacterData` interface (i.e.,
 *                    a `Text`, `Comment`, or `CDATASection` node)
 * @return            `true` if all of the text content of `nod` is whitespace,
 *                    otherwise `false`.
 */
function isAllWhitespace(node) {
    return !/[^\t\n\r ]/.test(node.textContent);
}

/**
 * Recursively traverses the DOM and highlights text nodes based on the indices.
 *
 * @param {Node} node The current node to process.
 * @param {number} startIndex The starting character index.
 * @param {number} endIndex The ending character index.
 * @param {object} context An object holding the traversal state (characterCount, highlighting).
 */
function traverseAndHighlight(node, startIndex, endIndex, context) {
    if (context.characterCount > endIndex) return;

    // We only care about text nodes and element nodes.
    // We skip comments, etc.
    if (
        node.nodeType !== Node.ELEMENT_NODE &&
        node.nodeType !== Node.TEXT_NODE
    ) {
        return;
    }

    // If it's an element, recurse on its children
    if (node.nodeType === Node.ELEMENT_NODE) {
        // We must convert childNodes to an array because the DOM manipulation
        // ahead can change the live NodeList, causing issues with the loop.
        for (const child of Array.from(node.childNodes)) {
            traverseAndHighlight(child, startIndex, endIndex, context);
        }
        return;
    }

    // From here, we are only dealing with TEXT_NODE

    if (isAllWhitespace(node)) {
        if (!context.skipping_whitespace) {
            context.characterCount += 1;
            context.skipping_whitespace = true;
        }
        return;
    }

    const nodeText = node.textContent;
    const nodeLength =
        nodeText.length -
        nodeText.includes("¶") -
        (context.skipping_whitespace && nodeText.startsWith(" "));

    context.skipping_whitespace = nodeText.endsWith(" ");

    const startOfNode = context.characterCount;
    const endOfNode = startOfNode + nodeLength;

    // Update the global character count for the next node
    context.characterCount = endOfNode;

    // --- Core Logic: Determine if this node needs full or partial highlighting ---

    // Case 1: The highlight is entirely contained within this single text node.
    // [  start---end  ]
    if (
        !context.highlighting &&
        startOfNode <= startIndex &&
        endOfNode >= endIndex
    ) {
        context.first_node = node;
        const startOffset = startIndex - startOfNode;
        const endOffset = endIndex - startOfNode;

        // Split the node at the end index first
        const middleBit = node.splitText(startOffset);
        middleBit.splitText(endOffset - startOffset);

        // The middleBit is now the text to be highlighted
        wrapNode(middleBit);
        return;
    }

    // Case 2: The highlight starts here but ends in a later node.
    // [  start-------->
    if (
        !context.highlighting &&
        startOfNode <= startIndex &&
        endOfNode > startIndex
    ) {
        context.first_node = node;
        const offset = startIndex - startOfNode;
        const nodeToWrap = node.splitText(offset);
        wrapNode(nodeToWrap);
        context.highlighting = true; // Enter highlighting mode
        return;
    }

    // Case 3: This entire node is within the highlight range.
    // <---- full node ---->
    if (context.highlighting && endOfNode <= endIndex) {
        wrapNode(node);
        return;
    }

    // Case 4: The highlight started in a previous node and ends here.
    // <--------end   ]
    if (context.highlighting && endOfNode >= endIndex) {
        const offset = endIndex - startOfNode;
        node.splitText(offset); // The first part of the split is what we need to wrap
        wrapNode(node);
        context.highlighting = false; // We are done highlighting
        return;
    }
}

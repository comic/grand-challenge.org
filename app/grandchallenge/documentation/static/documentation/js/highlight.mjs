document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    const highlightText = params.get("highlight");

    if (highlightText) {
        const content = document.getElementById("pageContainer");
        const regex = new RegExp(highlightText, "i");

        const walker = document.createTreeWalker(
            content,
            NodeFilter.SHOW_TEXT,
            {
                acceptNode: node =>
                    regex.test(node.textContent)
                        ? NodeFilter.FILTER_ACCEPT
                        : NodeFilter.FILTER_SKIP,
            },
        );

        const node = walker.nextNode();
        if (node) {
            const span = document.createElement("span");
            span.textContent = node.textContent;
            span.innerHTML = node.textContent.replace(
                regex,
                match => `<mark>${match}</mark>`,
            );
            const tempDiv = document.createElement("div");
            tempDiv.innerHTML = span.innerHTML;

            node.parentNode.replaceChild(tempDiv.firstChild, node);

            // Scroll to the match
            tempDiv.firstChild.scrollIntoView({
                behavior: "smooth",
                block: "center",
            });
        }
    }
});

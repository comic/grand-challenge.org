document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    const highlightText = params.get("highlight");
    if (!highlightText) return;

    const content = document.getElementById("pageContainer");
    if (!content) return;

    const [startText, endText] = highlightText.split(":::");

    if (!startText) return;

    const elements = content.querySelectorAll("p, h3, h4, h5");

    let startNode = null;
    let capturing = false;

    for (const el of elements) {
        const text = el.textContent.replace(/\s+/g, " ");

        if (!startNode && text.includes(startText)) {
            startNode = el;
            capturing = true;
        }

        if (capturing) {
            el.classList.add("highlight");
        }

        if (!endText && startNode) break;

        if (endText && capturing && text.includes(endText)) break;
    }

    if (startNode) {
        startNode.scrollIntoView({ behavior: "smooth", block: "center" });
    }
});

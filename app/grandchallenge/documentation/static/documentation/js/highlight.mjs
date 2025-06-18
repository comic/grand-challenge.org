document.addEventListener("DOMContentLoaded", () => {
    const params = new URLSearchParams(window.location.search);
    const highlightText = params.get("highlight");

    if (highlightText) {
        const paragraphs = document.querySelectorAll(
            "#pageContainer p, #pageContainer h3, #pageContainer h4, #pageContainer h5",
        );
        const cleanText = highlightText.toLowerCase().replace(/[^\w\s]/g, "");

        let bestMatch = null;
        let maxMatchScore = 0;

        for (const el of paragraphs) {
            const content = el.textContent.toLowerCase();
            const score = content
                .split(" ")
                .filter(word => cleanText.includes(word)).length;

            if (score > maxMatchScore) {
                maxMatchScore = score;
                bestMatch = el;
            }
        }

        if (bestMatch) {
            bestMatch.classList.add("highlight");
            bestMatch.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    }
});

const activeTimers = {};
const originalTitles = {};

document.addEventListener("click", e => {
    const btn = e.target.closest(".copy-btn");
    if (!btn) return;

    const id = btn.dataset.copy;

    if (!originalTitles[id]) {
        originalTitles[id] = btn.title;
    }
    clearTimeout(activeTimers[id]);

    navigator.clipboard
        .writeText(id)
        .then(() => {
            $(btn)
                .tooltip({ trigger: "manual" })
                .attr("data-original-title", "Copied to clipboard!")
                .tooltip("show");

            activeTimers[id] = setTimeout(() => {
                $(btn).attr("title", originalTitles[id]).tooltip("hide");
            }, 2000);
        })
        .catch(() => {
            $(btn)
                .tooltip({ trigger: "manual" })
                .attr("data-original-title", "Copy failed!")
                .tooltip("show");

            activeTimers[id] = setTimeout(() => {
                $(btn).attr("title", originalTitles[id]).tooltip("hide");
            }, 2000);
        });
});

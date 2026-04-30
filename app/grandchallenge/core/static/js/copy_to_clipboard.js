document.addEventListener("DOMContentLoaded", () => {
    const activeTimers = {};
    const originalTitles = {};

    document.addEventListener("click", e => {
        const btn = e.target.closest(".copy-btn");
        if (!btn) return;

        const id = btn.dataset.copy;

        // Only store the title if we don't have it yet
        if (!originalTitles[id]) {
            originalTitles[id] = btn.title;
        }
        // Clear any timers that might already be present (e.g. because user double-clicked)
        clearTimeout(activeTimers[id]);

        navigator.clipboard.writeText(id).then(() => {
            $(btn)
                .tooltip({ trigger: "manual" })
                .attr("data-original-title", "Copied to clipboard!")
                .tooltip("show");

            activeTimers[id] = setTimeout(() => {
                $(btn).tooltip("dispose");
                btn.title = originalTitles[id];
            }, 2000);
        });
    });
});

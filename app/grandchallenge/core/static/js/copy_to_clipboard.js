document.addEventListener("DOMContentLoaded", () => {
    const activeTimers = {};
    const originalTitles = {};

    for (const btn of document.querySelectorAll(".copy-btn")) {
        btn.addEventListener("click", () => {
            const id = btn.dataset.copy;

            if (!originalTitles[id]) {
                originalTitles[id] = btn.title;
            }
            clearTimeout(activeTimers[id]);

            navigator.clipboard.writeText(id).then(() => {
                $(btn)
                    .tooltip({ trigger: "manual" })
                    .attr("data-original-title", "Copied to clipboard!")
                    .tooltip("show");

                activeTimers[id] = setTimeout(() => {
                    $(btn)
                        .attr("data-original-title", originalTitles[id])
                        .tooltip("hide");
                }, 2000);
            });
        });
    }
});

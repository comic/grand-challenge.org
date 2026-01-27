const initSelects = () => {
    const elements = document.querySelectorAll(
        "select[id^='id_flexible_widget_choice__INTERFACE_FIELD__']",
    );
    for (const el of elements) {
        const searchWidget = document.getElementById(
            `div_${el.id.replace(/^id_flexible_widget_choice/, "id_flexible_search")}`,
        );
        const uploadWidget = document.getElementById(
            `div_${el.id.replace(/^id_flexible_widget_choice/, "id_flexible_upload")}`,
        );

        if (!searchWidget || !uploadWidget) {
            continue;
        }

        // Run this every time, regardless of whether the event listener was added.
        // This ensures only the selected widget is displayed when the form is re-rendered after validation errors.
        searchWidget.classList.toggle("d-none", el.value !== "SEARCH");
        uploadWidget.classList.toggle("d-none", el.value !== "UPLOAD");

        // Add the event listener only once, otherwise we'll respond to the event multiple times.
        if (!el.dataset.eventListenerAdded) {
            el.addEventListener("change", function () {
                searchWidget.classList.toggle(
                    "d-none",
                    this.value !== "SEARCH",
                );
                uploadWidget.classList.toggle(
                    "d-none",
                    this.value !== "UPLOAD",
                );
            });
            el.dataset.eventListenerAdded = "1";
        }
    }
};

document.addEventListener("htmx:load", initSelects);

initSelects();

$("document").ready(() => {
    // Sync the height of the preview element to the height of the editor element.
    const ELEMENTS = document.getElementsByClassName("markdownx");
    Object.values(ELEMENTS).map(element => {
        const editor = element.querySelector(".markdownx-editor");
        const preview = element.querySelector(".markdownx-preview");
        preview.style.height = `${editor.clientHeight}px`;
        const resizeObserver = new ResizeObserver(entries => {
            for (const entry of entries) {
                if (entry.contentBoxSize) {
                    preview.style.height = `${editor.clientHeight}px`;
                }
            }
        });
        resizeObserver.observe(editor);
    });
});

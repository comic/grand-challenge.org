// Sync the height of the preview element to the height of the editor element.
// This lets the user adjust the height of both elements by resizing the editor.
document.addEventListener("DOMContentLoaded", function() {
    const elements = document.getElementsByClassName("markdownx");
    for (const element of elements) {
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
    }
});

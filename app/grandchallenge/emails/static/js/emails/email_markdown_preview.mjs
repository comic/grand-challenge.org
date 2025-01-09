document.addEventListener("DOMContentLoaded", event => {
    const iframes = document.querySelectorAll(".markdownx-preview");
    for (const iframe of iframes) {
        const observer = new MutationObserver(() => {
            iframe.srcdoc = iframe.innerHTML;
        });
        observer.observe(iframe, {
            childList: true,
        });
    }
});

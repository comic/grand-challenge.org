document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("unsubscribeForm");
    if (form.classList.contains("auto-submit")) {
        form.submit();
    }
});

function enableElements() {
    const elements = document.querySelectorAll("[hx-enable-me]");
    for (const element of elements) {
        element.removeAttribute("disabled");
        element.removeAttribute("hx-enable-me");
    }
}

document.addEventListener("htmx:load", enableElements);
document.addEventListener("DOMContentLoaded", enableElements);

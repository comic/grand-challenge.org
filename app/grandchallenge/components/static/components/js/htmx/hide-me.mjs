function hideElements() {
    const elements = document.querySelectorAll("[hx-hide-me]");
    for (const element of elements) {
        element.classList.add("d-none");
        element.removeAttribute("hx-hide-me");
    }
}

document.addEventListener("htmx:load", hideElements);
document.addEventListener("DOMContentLoaded", hideElements);

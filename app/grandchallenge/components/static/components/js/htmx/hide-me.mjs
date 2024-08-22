function hideElements() {
    const elements = document.querySelectorAll("[hx-hide-me]");
    elements.forEach(element => {
        element.classList.add("d-none");
        element.removeAttribute("hx-hide-me");
    });
}

document.addEventListener("htmx:load", hideElements);
document.addEventListener("DOMContentLoaded", hideElements);

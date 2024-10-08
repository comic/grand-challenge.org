function displayElements() {
    const elements = document.querySelectorAll("[hx-display-me]");
    for (const element of elements) {
        element.classList.remove("d-none");
        element.removeAttribute("hx-display-me");
    }
}

document.addEventListener("htmx:load", displayElements);
document.addEventListener("DOMContentLoaded", displayElements);

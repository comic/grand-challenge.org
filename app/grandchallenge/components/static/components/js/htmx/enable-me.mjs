function enableElements() {
  const elements = document.querySelectorAll("[hx-enable-me]");
  elements.forEach(function (element) {
    element.removeAttribute("disabled");
    element.removeAttribute("hx-enable-me");
  });
}

document.addEventListener("htmx:load", enableElements);
document.addEventListener("DOMContentLoaded", enableElements);

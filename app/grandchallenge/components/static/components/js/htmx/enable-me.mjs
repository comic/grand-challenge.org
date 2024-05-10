document.addEventListener('DOMContentLoaded', (event) => {
    let elements = document.querySelectorAll('[hx-enable-me]');
    elements.forEach(function (element) {
        element.removeAttribute('disabled');
    });
});

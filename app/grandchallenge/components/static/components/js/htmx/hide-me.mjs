document.addEventListener('DOMContentLoaded', (event) => {
    let elements = document.querySelectorAll('[hx-hide-me]');
    elements.forEach(function(element) {
        element.classList.add('d-none');
    });
});

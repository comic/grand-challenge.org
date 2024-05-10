document.addEventListener('DOMContentLoaded', (event) => {
    let elements = document.querySelectorAll('[hx-display-me]');
    elements.forEach(function(element) {
        element.classList.remove('d-none');
    });
})

document.addEventListener('htmx:loaded', function() {
    let elements = document.querySelectorAll('[hx-hide-me]');
    elements.forEach(function(element) {
        element.classList.add('d-none');
    });
});

$(document).ready(() => {
    let elements = document.querySelectorAll("[id=image]");
    for(var i = 0, len = elements.length; i < len; i++) {
        if (elements[i].value) {
            htmx.trigger(elements[i], 'imageSelected');
        }
    }
});

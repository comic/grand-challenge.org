$(document).ready(() => {
    const elements = document.querySelectorAll("[id^=widgetSelect]");
    for (let i = 0, len = elements.length; i < len; i++) {
        if (elements[i].value === "IMAGE_SEARCH") {
            htmx.trigger(elements[i], "widgetSelected");
        }
    }
});

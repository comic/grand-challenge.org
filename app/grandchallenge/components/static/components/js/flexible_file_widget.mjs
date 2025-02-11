$(document).ready(() => {
    const elements = document.querySelectorAll("[id^=widget-select]");
    for (let i = 0, len = elements.length; i < len; i++) {
        if (elements[i].value === "FILE_SEARCH") {
            htmx.trigger(elements[i], "widgetSelected");
        }
    }
});

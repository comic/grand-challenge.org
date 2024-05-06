// HTMX does not have an init event, this is a proxy

const loadedEvt = new Event("htmx:loaded");
document.getElementById('htmx-script').onload = () => {
    document.dispatchEvent(loadedEvt);
};

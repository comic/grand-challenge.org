document.body.addEventListener('htmx:beforeSwap', function(evt) {
    if(evt.detail.xhr.responseText.includes('<!DOCTYPE html>')){
        // if the response is an entire html page, make sure hx-target is the document body
        evt.detail.target = htmx.find("body")
    }
});

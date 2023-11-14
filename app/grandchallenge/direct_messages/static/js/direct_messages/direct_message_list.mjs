document.body.addEventListener("htmx:afterOnLoad", function(evt) {
    let conversationDetail = document.getElementById("conversation-detail");
    conversationDetail.scrollTop = conversationDetail.scrollHeight;

    for (let elm of document.getElementsByClassName("direct-message-select")) {
        elm.classList.remove("active");
    }
    evt.target.classList.add("active");
});

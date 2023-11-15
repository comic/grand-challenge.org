document.body.addEventListener("htmx:afterOnLoad", function(evt) {
    let conversationDetail = document.getElementById("conversation-direct-messages-panel");
    conversationDetail.scrollTop = conversationDetail.scrollHeight;

    if (evt.target.classList.contains("conversation-detail-select")) {
        // Event was from switching the conversation detail
        for (let elm of document.getElementsByClassName("conversation-detail-select")) {
            elm.classList.remove("active");
        }
        evt.target.classList.add("active");

        // TODO mark the conversation as read

        //  TODO remove the unread button
    } else if (evt.target.id === "conversation-detail-panel") {
        // Event was from creating a new message in a conversation

        // TODO update the message text and time in the conversation detail select
    }
});

document.body.addEventListener("htmx:afterOnLoad", function(evt) {
    let conversationDetail = document.getElementById("conversation-direct-messages-panel");
    conversationDetail.scrollTop = conversationDetail.scrollHeight;

    if (evt.target.classList.contains("conversation-detail-select")) {
        // Event was from switching the conversation detail

        // Mark this conversation select as active
        for (let elm of document.getElementsByClassName("conversation-detail-select")) {
            elm.classList.remove("active");
        }
        evt.target.classList.add("active");

        let markReadForm = evt.target.querySelector('.conversation-mark-read-form');
        if (markReadForm !== null) {
            // Mark the form as read
            fetch(markReadForm.action, {
                method: markReadForm.method,
                body: new URLSearchParams(new FormData(markReadForm)),
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            }).then(
                (response) => {
                    // Update the conversation select button
                    htmx.ajax('GET', evt.target.dataset.conversationSelectDetailUrl, evt.target);
                }
            );
        }
    } else if (evt.target.id === "conversation-detail-panel") {
        // Event was from creating a new message in a conversation

        // Update the conversation select button
        let directMessagePanel = evt.target.querySelector("#conversation-direct-messages-panel");
        htmx.ajax('GET', directMessagePanel.dataset.conversationSelectDetailUrl, directMessagePanel.dataset.conversationSelectButtonSelector)
    }
});

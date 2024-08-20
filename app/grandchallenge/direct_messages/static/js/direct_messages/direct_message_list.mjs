document.addEventListener("DOMContentLoaded", function () {
    // Jump to targeted conversation
    const urlParams = new URLSearchParams(window.location.search);
    const conversationId = urlParams.get("conversation");

    if (conversationId !== null) {
        document
            .getElementById(`conversation-select-button-${conversationId}`)
            .click();
    }
});

document.body.addEventListener("htmx:afterOnLoad", function (evt) {
    // Scroll to bottom of message panel
    let conversationDetail = document.getElementById(
        "conversation-direct-messages-panel",
    );
    conversationDetail.scrollTop = conversationDetail.scrollHeight;

    document.getElementById("id_message").focus();

    if (evt.target.classList.contains("conversation-detail-select")) {
        // Event was from switching the conversation detail

        // Mark this conversation select as active
        for (let elm of document.getElementsByClassName(
            "conversation-detail-select",
        )) {
            elm.classList.remove("active");
        }
        evt.target.classList.add("active");

        const url = new URL(location);
        url.searchParams.set("conversation", evt.target.dataset.conversationId);
        history.pushState({}, "", url);

        let markReadForm = evt.target.querySelector(
            ".conversation-mark-read-form",
        );
        if (markReadForm !== null) {
            // Mark the form as read
            fetch(markReadForm.action, {
                method: markReadForm.method,
                body: new URLSearchParams(new FormData(markReadForm)),
                headers: {
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            }).then((response) => {
                // Update the conversation select button
                htmx.ajax(
                    "GET",
                    evt.target.dataset.conversationSelectDetailUrl,
                    evt.target,
                );
            });
        }
    } else if (evt.target.id === "conversation-detail-panel") {
        // Event was from creating a new message in a conversation

        // Update the conversation select button
        let directMessagePanel = evt.target.querySelector(
            "#conversation-direct-messages-panel",
        );
        htmx.ajax(
            "GET",
            directMessagePanel.dataset.conversationSelectDetailUrl,
            directMessagePanel.dataset.conversationSelectButtonSelector,
        );
    }
});

"use strict";

(function () {
    document.addEventListener("DOMContentLoaded", function (event) {
        const widgets = document.getElementsByClassName("user-upload");
        for (const widget of widgets) {
            initializeWidget(widget)
        }
    });

    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    function initializeWidget(widget) {
        const createUploadUrl = widget.getAttribute("data-createUploadUrl");
        const csrftoken = getCookie('_csrftoken');

        fetch(
            createUploadUrl,
            {
                method: "POST",
                credentials: "include",
                headers: {
                    "X-CSRFToken": csrftoken
                }
            }
        ).then(response => response.json()
        ).then(upload => setWidgetAttrs(widget, upload));
    }

    function setWidgetAttrs(widget, upload) {
        widget.setAttribute("data-uploadPk", upload.pk);
    }
})();

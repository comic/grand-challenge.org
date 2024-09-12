const csrfToken = JSON.parse(document.getElementById("csrfToken").textContent);

document.body.addEventListener("htmx:configRequest", event => {
    event.detail.headers["X-CSRFToken"] = csrfToken;
});

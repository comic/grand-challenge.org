document.addEventListener("DOMContentLoaded", event => {
    document.getElementById("emailBodyFrame").srcdoc = JSON.parse(
        document.getElementById("renderedBody").textContent,
    );
});

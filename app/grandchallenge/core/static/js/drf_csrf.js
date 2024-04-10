const csrfHeaderName = JSON.parse(document.getElementById('csrfHeaderName').textContent);
const csrfToken = JSON.parse(document.getElementById('csrfToken').textContent);

window.drf = {
    csrfHeaderName: csrfHeaderName,
    csrfToken: csrfToken
};

const drfDiv = document.getElementById("drf_csrf");
drfDiv.textContent = JSON.stringify(window.drf);

const csrfHeaderName = JSON.parse(document.getElementById('csrfHeaderName').textContent);
const csrfToken = JSON.parse(document.getElementById('csrfToken').textContent);

window.drf = {
    csrfHeaderName: csrfHeaderName,
    csrfToken: csrfToken
};

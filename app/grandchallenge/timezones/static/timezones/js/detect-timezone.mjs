const setTimezoneUrl = JSON.parse(document.getElementById('setTimezoneUrl').textContent);
const currentTimezone = JSON.parse(document.getElementById('currentTimezone').textContent);

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

async function updateTimezone() {
    const csrftoken = getCookie("_csrftoken");
    const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;

    if (timeZone !== currentTimezone && csrftoken !== null) {
        return fetch(setTimezoneUrl, {
            method: 'PUT',
            headers: {
                'X-CSRFToken': csrftoken,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({'timezone': timeZone}),
        });
    }
}

updateTimezone();

const setTimezoneUrl = JSON.parse(document.getElementById('setTimezoneUrl').textContent);

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

    if (csrftoken !== null && timeZone !== undefined) {
        let dataForm = new FormData();

        dataForm.append('timezone', timeZone);
        dataForm.append('csrfmiddlewaretoken', csrftoken);

        return await fetch(setTimezoneUrl, {
            method: 'POST',
            mode: 'same-origin',
            body: dataForm,
        });
    }
}

updateTimezone();

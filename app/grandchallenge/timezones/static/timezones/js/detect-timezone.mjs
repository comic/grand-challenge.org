import { getCookie } from "../../js/get_cookie.mjs";

const setTimezoneUrl = JSON.parse(
    document.getElementById("setTimezoneUrl").textContent,
);
const currentTimezone = JSON.parse(
    document.getElementById("currentTimezone").textContent,
);

async function updateTimezone() {
    const csrftoken = getCookie("_csrftoken");
    const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;

    if (timeZone !== currentTimezone && csrftoken !== null) {
        return fetch(setTimezoneUrl, {
            method: "PUT",
            headers: {
                "X-CSRFToken": csrftoken,
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ timezone: timeZone }),
        });
    }
}

updateTimezone();

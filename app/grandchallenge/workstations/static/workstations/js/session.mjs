const timeout = 1000;
const max_attempts = 60;

const params = new URLSearchParams(window.location.search);
const path = decodeURIComponent(params.has("path") ? params.get("path") : "");
const qs = decodeURIComponent(params.has("qs") ? params.get("qs") : "");
const workstationUrl = JSON.parse(
    document.getElementById("workstationUrl").textContent,
);
const workstationUrlWithQuery = `${workstationUrl}/${path}?${qs}`;
const sessionDetailUrl = JSON.parse(
    document.getElementById("sessionDetailUrl").textContent,
);

const modal = $("#sessionModal");

function getSessionStatus(statusUrl, statusButton, workstationUrl) {
    // Checks on the status of the Session (queued, running, started, etc)

    fetch(statusUrl, { credentials: "include" })
        .then(response => response.json())
        .then(session =>
            handleSessionStatus(
                statusUrl,
                statusButton,
                session.status,
                workstationUrl,
            ),
        );
}

function handleSessionStatus(statusUrl, statusButton, status, workstationUrl) {
    switch (status.toLowerCase()) {
        case "queued":
            setButtonLoadingMessage(
                statusButton,
                "Starting the workstation container...",
            );
            setTimeout(
                () => {
                    getSessionStatus(statusUrl, statusButton, workstationUrl);
                },
                Math.floor(Math.random() * timeout) + 100,
            );
            break;
        case "running":
        case "started":
            setButtonLoadingMessage(
                statusButton,
                "Waiting for the workstation to respond...",
            );
            redirectWhenReady(workstationUrl, statusButton, 0);
            break;
        case "failed":
        case "stopped":
            setButtonError(
                statusButton,
                `This session has ${status.toLowerCase()}.`,
            );
            break;
        default:
            setButtonError(statusButton, "Workstation is in an unknown state.");
    }
}

function redirectWhenReady(url, statusButton, attempts = 0) {
    // Redirects to the url if the status code is 200. Used to poll if the
    // workstation http server is up and running yet.
    if (attempts === max_attempts) {
        setButtonError(statusButton, "Could not connect to workstation");
        return;
    }

    fetch(url)
        .then(response => response.status)
        .then(status => {
            if (status === 200) {
                window.location.replace(url);
            } else {
                // Workstation not responding yet
                setTimeout(
                    () => {
                        redirectWhenReady(url, statusButton, attempts + 1);
                    },
                    Math.floor(Math.random() * timeout) + 100,
                );
            }
        });
}

function setButtonLoadingMessage(statusButton, msg) {
    statusButton.querySelector("#sessionStateMsg").innerHTML = msg;
}

function setButtonError(statusButton, msg) {
    statusButton.querySelector("#sessionStateBody").innerHTML = `<b>${msg}</b>`;
    statusButton
        .querySelector("#sessionStateFooter")
        .classList.remove("d-none");
}

modal.on("shown.bs.modal", e => {
    getSessionStatus(
        sessionDetailUrl,
        document.getElementById("sessionState"),
        workstationUrlWithQuery,
    );
});

modal.modal("show");

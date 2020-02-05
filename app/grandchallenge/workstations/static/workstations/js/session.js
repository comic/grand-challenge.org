"use strict";

const timeout = 1000;
const max_attempts = 60;

function getSessionStatus(statusUrl, statusButton, workstationUrl) {
    // Checks on the status of the Session (queued, running, started, etc)

    fetch(statusUrl)
        .then(response => response.json())
        .then(session => handleSessionStatus(statusUrl, statusButton, session.status, workstationUrl));
}

function handleSessionStatus(statusUrl, statusButton, status, workstationUrl) {
    switch (status.toLowerCase()) {
        case "queued":
            setButtonLoadingMessage(statusButton, "Starting the workstation container...");
            setTimeout(function () {
                getSessionStatus(statusUrl, statusButton, workstationUrl)
            }, Math.floor(Math.random() * timeout) + 100);
            break;
        case "running":
        case "started":
            setButtonLoadingMessage(statusButton, "Waiting for the workstation to respond...");
            redirectWhenReady(workstationUrl, statusButton);
            break;
        case "failed":
        case "stopped":
            setButtonError(statusButton, "This session has " + status.toLowerCase() + ".");
            break;
        default:
            setButtonError(statusButton, "Workstation is in an unknown state.");
    }
}

function redirectWhenReady(url, statusButton, attempts = 0) {
    // Redirects to the url if the status code is 200. Used to poll if the
    // workstation http server is up and running yet.

    attempts = Number(attempts);
    if (attempts === max_attempts) {
        setButtonError(statusButton, "Could not connect to workstation");
        return
    }

    fetch(url)
        .then(response => response.status)
        .then(
            function (status) {
                if (status === 200) {
                    window.location.replace(url);
                } else {
                    // Workstation not responding yet
                    setTimeout(function () {
                        redirectWhenReady(url, statusButton, attempts + 1)
                    }, Math.floor(Math.random() * timeout) + 100);
                }
            }
        )
}

function setButtonLoadingMessage(statusButton, msg) {
    statusButton.querySelector("#sessionStateMsg").innerHTML = msg;
}

function setButtonError(statusButton, msg) {
    statusButton.querySelector("#sessionStateBody").innerHTML = "<b>" + msg + "</b>";
    statusButton.querySelector("#sessionStateFooter").classList.remove("d-none");
}

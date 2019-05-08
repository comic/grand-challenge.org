"use strict";

const timeout = 1000;

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
            }, timeout);
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

function redirectWhenReady(url, statusButton) {
    // Redirects to the url if the status code is 200. Used to poll if the
    // workstation http server is up and running yet.

    fetch(url)
        .then(response => response.status)
        .then(
            function (status) {
                switch (status) {
                    case 200:
                        window.location.replace(url);
                        break;
                    case 502:
                        // Workstation not responding yet
                        setTimeout(function () {
                            redirectWhenReady(url, statusButton)
                        }, timeout);
                        break;
                    default:
                        setButtonError(statusButton, "Could not connect to workstation");
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

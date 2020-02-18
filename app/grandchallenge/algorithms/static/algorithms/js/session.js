"use strict";

const timeout = 1000;

function getUploadSessionStatus(statusUrl, statusButton) {
    // Checks on the status of the Session (queued, running, started, etc)
    fetch(statusUrl)
        .then(response => response.json())
        .then(session => handleUploadSessionStatus(statusUrl, statusButton, session.status, session.image_set));
}

function handleUploadSessionStatus(statusUrl, statusButton, status, imageSet) {
    switch (status.toLowerCase()) {
        case "queued":
        case "re-queued":
            setButtonLoadingMessage(statusButton, "Awaiting Resources...");
            setTimeout(function () {
                getUploadSessionStatus(statusUrl, statusButton)
            }, Math.floor(Math.random() * timeout) + 100);
            break;
        case "started":
            setButtonLoadingMessage(statusButton, "Importing Images...");
            setTimeout(function () {
                getUploadSessionStatus(statusUrl, statusButton)
            }, Math.floor(Math.random() * timeout) + 100);
            break;
        case "succeeded":
            console.log("Created images: " + imageSet);
            getJobsForImages(imageSet);
            break;
        case "failed":
        case "cancelled":
            setButtonError(statusButton, "This session has " + status.toLowerCase() + ".");
            break;
        default:
            setButtonError(statusButton, "Workstation is in an unknown state.");
    }
}

function getJobsForImages(imageSet) {
    Promise.all(imageSet.map(url => fetch(url).then(response => response.json()))
    ).then(images => {
        getJobStatus(images.map(i => i.job_set).flat());
    });
}

function getJobStatus(jobSet) {
    Promise.all(jobSet.map(url => fetch(url).then(response => response.json()))
    ).then(jobs => {
        getResults(jobs.map(j => j.result));
        // TODO check that all the jobs have succeeded
    });
}

function getResults(resultSet) {
    Promise.all(resultSet.map(url => fetch(url).then(response => response.json()))
    ).then(results => {
        getResultImportStatus(results.map(r => r.rawimageuploadsession));
    });
}

function getResultImportStatus(resultImportSessionSet) {
    Promise.all(resultImportSessionSet.map(url => fetch(url).then(response => response.json()))
    ).then(importSessionSet => {
        console.log(importSessionSet);
    });
}

function setButtonLoadingMessage(statusButton, msg) {
    console.log(msg);
    //statusButton.querySelector("#sessionStateMsg").innerHTML = msg;
}

function setButtonError(statusButton, msg) {
    console.log(msg);
    //statusButton.querySelector("#sessionStateBody").innerHTML = "<b>" + msg + "</b>";
    //statusButton.querySelector("#sessionStateFooter").classList.remove("d-none");
}

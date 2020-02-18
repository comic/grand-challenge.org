"use strict";

const timeout = 1000;

function getUploadSessionStatus(statusUrl, cards) {
    // Checks on the status of the Session (queued, running, started, etc)
    fetch(statusUrl)
        .then(response => response.json())
        .then(session => handleUploadSessionStatus(statusUrl, cards, session.status, session.image_set));
}

function handleUploadSessionStatus(statusUrl, cards, status, imageSet) {
    switch (status.toLowerCase()) {
        case "queued":
        case "re-queued":
            setCardAwaitingMessage(cards.imageImport, status);
            setTimeout(function () {
                getUploadSessionStatus(statusUrl, cards.imageImport)
            }, Math.floor(Math.random() * timeout) + 100);
            break;
        case "started":
            setCardActiveMessage(cards.imageImport, status);
            setTimeout(function () {
                getUploadSessionStatus(statusUrl, cards.imageImport)
            }, Math.floor(Math.random() * timeout) + 100);
            break;
        case "succeeded":
            var msg = "Imported " + imageSet.length + " Image";
            if (imageSet.length < 1) {
                setCardErrorMessage(cards.imageImport, "No Images Imported");
                return;
            } else if (imageSet.length > 1 ) {
                msg += "s"
            }
            setCardCompleteMessage(cards.imageImport, msg);
            getJobsForImages(imageSet, cards);
            break;
        case "failed":
        case "cancelled":
            setCardErrorMessage(cards.imageImport, status);
            break;
        default:
            setCardErrorMessage(cards.imageImport, "Import error");
    }
}

function getJobsForImages(imageSet, cards) {
    setCardAwaitingMessage(cards.job, "Fetching Status");

    Promise.all(imageSet.map(url => fetch(url).then(response => response.json()))
    ).then(images => {
        getJobStatus(images.map(i => i.job_set).flat(), cards);
    });
}

function getJobStatus(jobSet, cards) {
    Promise.all(jobSet.map(url => fetch(url).then(response => response.json()))
    ).then(jobs => {
        handleJobStatus(jobs, cards);
    });
}

function handleJobStatus(jobSet, cards) {
    var jobStatuses = jobSet.map(j => j.status.toLowerCase());

    if (jobStatuses.every(s => s === "succeeded")) {
        setCardCompleteMessage(cards.job, "");
        getResults(jobSet.map(j => j.result), cards);
    }

    // TODO: handle queued and failed jobs
}

function getResults(resultSet, cards) {
    setCardAwaitingMessage(cards.resultImport, "Fetching Status");

    Promise.all(resultSet.map(url => fetch(url).then(response => response.json()))
    ).then(results => {
        getResultImportStatus(results.map(r => r.rawimageuploadsession), cards);
    });

    // TODO: Handle results without import sessions
}

function getResultImportStatus(resultImportSessionSet, cards) {
    Promise.all(resultImportSessionSet.map(url => fetch(url).then(response => response.json()))
    ).then(importSessionSet => {
        handleImportSessionsStatus(importSessionSet, cards);
    });
}

function handleImportSessionsStatus(importSessionsSet, cards) {
    var importSessionStatuses = importSessionsSet.map(j => j.status.toLowerCase());

    if (importSessionStatuses.every(s => s === "succeeded")) {
        setCardCompleteMessage(cards.resultImport, "");
    }

    // TODO: handle queued and failed import jobs
}

function setCardAwaitingMessage(card, msg) {
    card.classList.replace("border-light", "border-primary");
    card.classList.remove("text-muted");
    card.querySelector(".statusMessage").innerHTML = msg;
    card.querySelector(".statusSymbol").innerHTML = "<i class=\"far fa-hourglass fa-2x\"></i>";
}

function setCardActiveMessage(card, msg) {
    console.log(msg);
    //statusButton.querySelector("#sessionStateMsg").innerHTML = msg;
}

function setCardCompleteMessage(card, msg) {
    card.classList.replace("border-primary", "border-success");
    card.querySelector(".statusMessage").innerHTML = msg;
    card.querySelector(".statusSymbol").innerHTML = "<i class=\"fa fa-check fa-2x\"></i>";
}

function setCardErrorMessage(card, msg) {
    console.log(msg);
    //statusButton.querySelector("#sessionStateBody").innerHTML = "<b>" + msg + "</b>";
    //statusButton.querySelector("#sessionStateFooter").classList.remove("d-none");
}

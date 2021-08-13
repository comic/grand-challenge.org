"use strict";

const timeout = 5000;

const cards = {
    "imageImport": document.getElementById("imageImportCard"),
    "job": document.getElementById("jobCard"),
    "resultImport": document.getElementById("resultImportCard")
};

const averageJobDuration = moment.duration(JSON.parse(document.getElementById("averageJobDuration").textContent));
const jobListApiUrl = JSON.parse(document.getElementById("jobListApiUrl").textContent);

// Set anything less than 1s to "a few seconds"
moment.relativeTimeThreshold('ss', 1);

function getUploadSessionStatus(statusUrl) {
    // Checks on the status of the Session (queued, running, started, etc)
    fetch(statusUrl)
        .then(response => response.json())
        .then(session => handleUploadSessionStatus(statusUrl, session.status, session.image_set));
}

function handleUploadSessionStatus(statusUrl, status, imageUrls) {
    switch (status.toLowerCase()) {
        case "queued":
        case "re-queued":
            setCardAwaitingMessage(cards.imageImport, status);
            setTimeout(function () {
                getUploadSessionStatus(statusUrl)
            }, Math.floor(Math.random() * timeout) + 100);
            break;
        case "started":
            setCardActiveMessage(cards.imageImport, status);
            setTimeout(function () {
                getUploadSessionStatus(statusUrl)
            }, Math.floor(Math.random() * timeout) + 100);
            break;
        case "succeeded":
            let msg = `Imported ${imageUrls.length} Image`;
            if (imageUrls.length < 1) {
                setCardErrorMessage(cards.imageImport, "No Images Imported");
                return;
            } else if (imageUrls.length > 1) {
                msg += "s"
            }
            setCardCompleteMessage(cards.imageImport, msg);
            getJobsForImages(imageUrls);
            break;
        case "failed":
        case "cancelled":
            setCardErrorMessage(cards.imageImport, status);
            break;
        default:
            setCardErrorMessage(cards.imageImport, "Import error");
    }
}

function getJobsForImages(imageUrls) {
    setCardAwaitingMessage(cards.job, "Fetching Status");

    Promise.all(imageUrls.map(url => fetch(url).then(response => response.json()))
    ).then(images => {
        let params = new URLSearchParams();
        images.forEach(i => params.append("input_image", i.pk));
        let jobUrl = `${jobListApiUrl}?${params.toString()}`;

        fetch(jobUrl)
            .then(response => response.json())
            .then(jobs => handleJobStatus(jobs.results))
    });
}

function getJobStatus(jobUrls) {
    Promise.all(jobUrls.map(url => fetch(url).then(response => response.json()))
    ).then(jobs => {
        handleJobStatus(jobs);
    });
}

function handleJobStatus(jobs) {
    let jobStatuses = jobs.map(j => j.status.toLowerCase());
    let jobUrls = jobs.map(j => j.api_url);

    let queuedJobs = jobStatuses.filter(s => ["queued", "re-queued"].includes(s)).length;
    let estimatedRemainingTime = queuedJobs * averageJobDuration;

    if (jobStatuses.some(s => s === "started")) {
        estimatedRemainingTime += averageJobDuration;
    }

    if (jobStatuses.every(s => s === "succeeded")) {
        setCardCompleteMessage(cards.job, "View Results");
    } else if (jobStatuses.some(s => ["started", "provisioning", "provisioned", "executing", "executed", "parsing outputs"].includes(s))) {
        setCardActiveMessage(cards.job, `Started, ${moment.duration(estimatedRemainingTime).humanize()} remaining`);
        setTimeout(function () {
            getJobStatus(jobUrls)
        }, Math.floor(Math.random() * timeout) + 100);
    } else if (jobStatuses.some(s => ["queued", "re-queued"].includes(s))) {
        setCardAwaitingMessage(cards.job, "Queued");
        setTimeout(function () {
            getJobStatus(jobUrls)
        }, Math.floor(Math.random() * timeout) + 100);
    } else {
        setCardErrorMessage(cards.job, "Errored");
    }
}

function setCardAwaitingMessage(card, msg) {
    card.classList.replace("border-light", "border-primary");
    card.classList.remove("text-muted", "active");
    card.querySelector(".statusMessage").innerHTML = msg;
    card.querySelector(".statusSymbol").innerHTML = "<div class=\"text-secondary spinner-grow\" role=\"status\"><span class=\"sr-only\">Loading...</span></div>";
}

function setCardActiveMessage(card, msg) {
    if (!card.classList.contains("active")) {
        card.classList.add("active");
        card.querySelector(".statusSymbol").innerHTML = "<div class=\"text-primary spinner-border\" role=\"status\"><span class=\"sr-only\">Loading...</span></div>";
    }
    card.querySelector(".statusMessage").innerHTML = msg;
}

function setCardCompleteMessage(card, msg) {
    card.classList.remove("active");
    card.classList.replace("border-primary", "border-success");
    card.querySelector(".statusMessage").innerHTML = msg;
    card.querySelector(".statusSymbol").innerHTML = "<i class=\"text-success fa fa-check fa-2x\"></i>";
}

function setCardErrorMessage(card, msg) {
    card.classList.remove("active", "text-muted", "border-primary", "border-success");
    card.classList.add("border-danger");
    card.querySelector(".statusMessage").innerHTML = msg;
    card.querySelector(".statusSymbol").innerHTML = "<i class=\"text-danger fa fa-times fa-2x\"></i>";
}

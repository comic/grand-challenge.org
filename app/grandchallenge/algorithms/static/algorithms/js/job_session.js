"use strict";

const timeout = 5000;

const cards = {
    "imageImport": document.getElementById("imageImportCard"),
    "job": document.getElementById("jobCard"),
    "resultImport": document.getElementById("resultImportCard")
};

const averageJobDuration = moment.duration(JSON.parse(document.getElementById("averageJobDuration").textContent));

// Set anything less than 1s to "a few seconds"
moment.relativeTimeThreshold('ss', 1);

function getJobStatus(jobUrl) {
    // Checks on the status of the Job (queued, running, started, etc)
    fetch(jobUrl)
        .then(response => response.json())
        .then(job => handleJobStatus(job));
}

function handleJobStatus(job) {
    let jobStatus = job.status.toLowerCase();
    let imageInputs = job.inputs.filter(i => ["Image","Heat Map","Segmentation"].includes(i.interface.kind));

    handleImageImports(jobStatus, imageInputs)

    let estimatedRemainingTime = averageJobDuration;

    if (jobStatus === "succeeded") {
        setCardCompleteMessage(cards.job, "View Results");
    } else if (["started", "provisioning", "provisioned", "executing", "executed", "parsing outputs"].includes(jobStatus)) {
        setCardActiveMessage(cards.job, `Started, ${moment.duration(estimatedRemainingTime).humanize()} remaining`);
        setTimeout(function () {
            getJobStatus(job.api_url)
        }, Math.floor(Math.random() * timeout) + 100);
    } else if (jobStatus === "queued" || jobStatus === "re-queued") {
        setCardAwaitingMessage(cards.job, "Queued");
        setTimeout(function () {
            getJobStatus(job.api_url)
        }, Math.floor(Math.random() * timeout) + 100);
    } else {
        setCardErrorMessage(cards.job, "Errored");
    }
}

function handleImageImports(jobStatus, imageInputs){
    if (imageInputs.length == 0){
        setCardInactiveMessage(cards.imageImport, "No images for this job");
    } else if (imageInputs.every(i => i.image!= null)){
        const msg = `Total of ${imageInputs.length} images`;
        setCardCompleteMessage(cards.imageImport, msg);
    } else {
        const msg = `${imageInputs.filter(i => i.image != null).length} of ${imageInputs.length} images imported`;
        if (jobStatus == "queued" || jobStatus === "re-queued") {
            setCardAwaitingMessage(cards.imageImport, msg);
        } else {
            setCardErrorMessage(cards.imageImport, `Errored: ${msg}`);
        }
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
    card.classList.remove("active", "border-light", "border-primary",  "text-muted");
    card.classList.add("border-success");
    card.querySelector(".statusMessage").innerHTML = msg;
    card.querySelector(".statusSymbol").innerHTML = "<i class=\"text-success fa fa-check fa-2x\"></i>";
}

function setCardErrorMessage(card, msg) {
    card.classList.remove("active", "text-muted", "border-light", "border-primary", "border-success");
    card.classList.add("border-danger");
    card.querySelector(".statusMessage").innerHTML = msg;
    card.querySelector(".statusSymbol").innerHTML = "<i class=\"text-danger fa fa-times fa-2x\"></i>";
}

function setCardInactiveMessage(card, msg) {
    card.classList.remove("active");
    card.classList.replace("border-primary", "border-success");
    card.querySelector(".statusMessage").innerHTML = msg;
    card.querySelector(".statusSymbol").innerHTML = "<i class=\"text-success fa fa-minus fa-2x\"></i>";
}

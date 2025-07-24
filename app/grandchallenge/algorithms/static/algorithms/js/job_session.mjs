let numImageInputs = 0;
let numFileInputs = 0;

const algorithmDetailAPI = JSON.parse(
    document.getElementById("algorithmDetailAPI").textContent,
);
const interfacePk = JSON.parse(
    document.getElementById("interfacePk").textContent,
);
const jobDetailAPI = JSON.parse(
    document.getElementById("jobDetailAPI").textContent,
);
const averageJobDuration = moment.duration(
    JSON.parse(document.getElementById("averageJobDuration").textContent),
);

const timeout = 5000;

const cards = {
    imageImport: document.getElementById("imageImportCard"),
    fileImport: document.getElementById("fileImportCard"),
    job: document.getElementById("jobCard"),
    resultImport: document.getElementById("resultImportCard"),
};

// Set anything less than 1s to "a few seconds"
moment.relativeTimeThreshold("ss", 1);

function getAlgorithmDetails(algorithmURL) {
    return fetch(algorithmURL)
        .then(response => response.json())
        .then(data => {
            const targetInterface = data.interfaces.find(
                i => i.pk === interfacePk,
            );

            if (!targetInterface || !Array.isArray(targetInterface.inputs)) {
                throw new Error(
                    `Interface with pk=${interfacePk} not found or missing inputs.`,
                );
            }

            const inputs = targetInterface.inputs;
            numImageInputs = inputs.filter(
                i => i.super_kind === "Image",
            ).length;
            numFileInputs = inputs.filter(i => i.super_kind === "File").length;
        });
}

function getJobStatus(jobUrl) {
    fetch(jobUrl)
        .then(response => response.json())
        .then(handleJobStatus)
        .catch(err => console.error("Failed to fetch job status:", err));
}

function handleJobStatus(job) {
    const jobStatus = job.status.toLowerCase();

    const imageInputs = job.inputs.filter(i =>
        ["Image", "Heat Map", "Segmentation"].includes(i.interface.kind),
    );

    const fileInputs = job.inputs.filter(
        i => i.interface.super_kind === "File",
    );

    updateCardStatus(
        cards.imageImport,
        jobStatus,
        imageInputs,
        numImageInputs,
        "image",
    );
    updateCardStatus(
        cards.fileImport,
        jobStatus,
        fileInputs,
        numFileInputs,
        "file",
    );

    if (jobStatus === "succeeded") {
        setCardCompleteMessage(cards.job, "View Results");
    } else if (
        [
            "validating inputs",
            "started",
            "provisioning",
            "provisioned",
        ].includes(jobStatus)
    ) {
        setCardActiveMessage(cards.job, "Job is being provisioned");
    } else if (
        ["executing", "executed", "parsing outputs"].includes(jobStatus)
    ) {
        setCardActiveMessage(
            cards.job,
            `Job is being executed <br> Average job duration: ${moment.duration(averageJobDuration).humanize()}`,
        );
    } else if (["queued", "re-queued"].includes(jobStatus)) {
        setCardAwaitingMessage(cards.job, "Queued");
    } else {
        setCardErrorMessage(cards.job, "Errored");
    }

    if (
        [
            "started",
            "validating inputs",
            "provisioning",
            "provisioned",
            "executing",
            "executed",
            "parsing outputs",
            "queued",
            "re-queued",
        ].includes(jobStatus)
    ) {
        setTimeout(
            () => getJobStatus(job.api_url),
            Math.floor(Math.random() * timeout) + 100,
        );
    }
}

function updateCardStatus(card, jobStatus, inputs, expectedCount, typeLabel) {
    if (expectedCount === 0) {
        setCardInactiveMessage(card, `No ${typeLabel}s for this job`);
        return;
    }

    const importedCount = inputs.filter(i => i[typeLabel] != null).length;
    const msg = `${importedCount} of ${expectedCount} ${typeLabel}s imported`;

    const isNotPending = !["queued", "re-queued", "validating inputs"].includes(
        jobStatus,
    );
    const isIncomplete = importedCount < expectedCount;

    if (isNotPending && isIncomplete) {
        setCardErrorMessage(card, msg);
    } else if (isIncomplete) {
        setCardAwaitingMessage(card, msg);
    } else {
        setCardCompleteMessage(card, msg);
    }
}

function setCardAwaitingMessage(card, msg) {
    card.classList.replace("border-light", "border-primary");
    card.classList.remove("text-muted", "active");
    card.querySelector(".statusMessage").innerHTML = msg;
    card.querySelector(".statusSymbol").innerHTML =
        '<div class="text-secondary spinner-grow" role="status"><span class="sr-only">Loading...</span></div>';
}

function setCardActiveMessage(card, msg) {
    if (!card.classList.contains("active")) {
        card.classList.add("active");
        card.querySelector(".statusSymbol").innerHTML =
            '<div class="text-primary spinner-border" role="status"><span class="sr-only">Loading...</span></div>';
    }
    card.querySelector(".statusMessage").innerHTML = msg;
}

function setCardCompleteMessage(card, msg) {
    card.classList.remove(
        "active",
        "border-light",
        "border-primary",
        "text-muted",
    );
    card.classList.add("border-success");
    card.querySelector(".statusMessage").innerHTML = msg;
    card.querySelector(".statusSymbol").innerHTML =
        '<i class="text-success fa fa-check fa-2x"></i>';
}

function setCardErrorMessage(card, msg) {
    card.classList.remove(
        "active",
        "text-muted",
        "border-light",
        "border-primary",
        "border-success",
    );
    card.classList.add("border-danger");
    card.querySelector(".statusMessage").innerHTML = msg;
    card.querySelector(".statusSymbol").innerHTML =
        '<i class="text-danger fa fa-times fa-2x"></i>';
}

function setCardInactiveMessage(card, msg) {
    card.classList.remove("active");
    card.classList.replace("border-primary", "border-success");
    card.querySelector(".statusMessage").innerHTML = msg;
    card.querySelector(".statusSymbol").innerHTML =
        '<i class="text-success fa fa-minus fa-2x"></i>';
}

getAlgorithmDetails(algorithmDetailAPI)
    .then(() => getJobStatus(jobDetailAPI))
    .catch(err => console.error("Failed to initialize:", err));

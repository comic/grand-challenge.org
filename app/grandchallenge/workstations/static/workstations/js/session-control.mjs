'use strict';

function openWorkstationSession(element) {
    return (event) => {
        const windowIdentifier = element.dataset.workstationWindowIdentifier;
        const url = element.dataset.createSessionUrl;
        const query = element.dataset.workstationQuery;
        const creationURI = `${url}?${query}`;
        const timeout = element.dataset.timeout || 1000;

        if (event.ctrlKey) {
            window.open(creationURI);
            return;
        }

        if (event.altKey) {
            copyTextToClipboard(query);
            return;
        }

        setSpinner(element);

        const potentialSessionOrigins = JSON.parse(document.getElementById('workstation-domains').textContent);
        const workstationWindow = window.open('', windowIdentifier);

        // check if we just opened a blank or existing context
        let isBlankContext = false;
        try {
            isBlankContext = workstationWindow.document.location.href === "about:blank";
        } catch (err) {
            // ignore any errors with getting the href as it entails we did not open
            // the context
            console.warn(err);
        }

        if (workstationWindow === null || isBlankContext) {
            createNewSessionWindow(creationURI, windowIdentifier, element);
        } else {
            const fallback = setTimeout(() => {
                // Assume window is non-responsive
                createNewSessionWindow(creationURI, windowIdentifier, element);
            }, timeout);

            potentialSessionOrigins.forEach((origin) => {
                sendSessionControlMessage(workstationWindow, origin, {loadQuery: query}, () => {
                    clearTimeout(fallback)
                }, element);
            });
        }
    }
}

function hookSessionControllers() {
    const sessionControllerElements = document.querySelectorAll('[data-session-control]');
    for (const element of sessionControllerElements) {
        element.onclick = openWorkstationSession(element);
    }
}

function sendSessionControlMessage(targetWindow, origin, action, ackCallback, triggeringElement) {
    const messageId = UUIDv4();
    const msg = {
        sessionControl: {
            meta: {
                id: messageId
            },
            ...action,
        }
    };
    targetWindow.postMessage(msg, origin);

    function checkAckMessage(event) {
        const receivedMsg = event.data.sessionControl;
        if (!receivedMsg) {
            return
        }
        const ack = receivedMsg.meta.acknowledge;
        if (!ack) {
            return
        }
        if (ack.id === messageId) {
            ackCallback();
            targetWindow.focus(); // absolutely necessary in Firefox, in Chrome/Edge window.open() already focusses the window
            removeSpinner(triggeringElement);
            window.removeEventListener('message', checkAckMessage);
        }
    }

    window.addEventListener('message', checkAckMessage);
}

function UUIDv4() {
    return ([1e7] + -1e3 + -4e3 + -8e3 + -1e11).replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
    );
}

function copyTextToClipboard(text) {
    const blob = new Blob([text], {type: "text/plain"});
    const data = [new ClipboardItem({ "text/plain": blob })];
    navigator.clipboard.write(data).then(function () {
        console.log("Copied to clipboard successfully!");
    });
}

function setSpinner(element) {
    element.querySelector("i").style.display = "none";
    const spinner = document.createElement("span");
    spinner.classList.add("spinner-border", "spinner-border-sm");
    element.prepend(spinner);
}

function removeSpinner(element) {
    const spinner = element.querySelector("span");
    element.removeChild(spinner);
    element.querySelector("i").style.display = "inline-block";
}

function createNewSessionWindow(creationURI, windowIdentifier, triggeringElement){
    window.open(creationURI, windowIdentifier);
    removeSpinner(triggeringElement);
}

$(document).ready(() => {
    // Run default once
    hookSessionControllers();

    // Sometimes content insertion is deferred and might result in adding session-control elements later:
    //  add listeners:

    // ajax-based tables
    $('#ajaxDataTable').on('draw.dt', () => {
        hookSessionControllers()
    });

    // htmx-based tables
    htmx.onLoad(function () {
        hookSessionControllers()
    });
});

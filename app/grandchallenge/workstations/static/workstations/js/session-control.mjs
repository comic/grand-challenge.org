'use strict';

function openWorkstationSession(element) {
    return (event) => {
        const windowIdentifier = element.dataset.workstationWindowIdentifier;
        const url = element.dataset.createSessionUrl;
        const query = element.dataset.workstationQuery;
        const creationURI = `${url}?${query}`;
        const timeout = element.dataset.timeout || 3000;

        if (event.ctrlKey) {
            window.open(creationURI);
            return;
        }

        if (event.altKey) {
            copyTextToClipboard(query);
            return;
        }

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
            window.open(creationURI, windowIdentifier);
        } else {
            workstationWindow.focus();

            const fallback = setTimeout(() => {
                // Assume window is non-responsive
                window.open(creationURI, windowIdentifier);
            }, timeout);

            potentialSessionOrigins.forEach((origin) => {
                sendSessionControlMessage(workstationWindow, origin, {loadQuery: query}, () => {
                    clearTimeout(fallback)
                });
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

function sendSessionControlMessage(targetWindow, origin, action, ackCallback) {
    const messageId = crypto.randomUUID();
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
            window.removeEventListener('message', checkAckMessage);
        }
    }

    window.addEventListener('message', checkAckMessage);
}

function copyTextToClipboard(text) {
    const blob = new Blob([text], {type: "text/plain"});
    const data = [new ClipboardItem({ "text/plain": blob })];
    navigator.clipboard.write(data).then(function () {
        console.log("Copied to clipboard successfully!");
    });
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

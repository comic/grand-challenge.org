'use strict';

function openWorkstationSession(element) {
    return (event) => {
        const windowIdentifier = element.dataset.workstationWindowIdentifier;
        const url = element.dataset.createSessionUrl;
        const query = element.dataset.workstationQuery;
        const creationURI = `${url}?${query}`;
        const domain = element.dataset.domain;
        const timeout = 3000;

        if (event.ctrlKey) {
            window.open(creationURI);
            return;
        }

        const regions = JSON.parse(document.getElementById('workstation-regions').textContent);
        const potentialSessionOrigins = getSessionOrigins(domain, regions);

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

        if (workstationWindow === null || isBlankContext ) {
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

function getSessionOrigins(hostname, regions) {
    const protocol = "https";
    const port = window.location.port;

    return regions.map((region) => `${protocol}://${region}.${hostname}${port ? ':' + port : ''}`);
}


function genSessionControllersHook() {
     const data = document.currentScript.dataset;
     const querySelector = (typeof data.sessionControlQuerySelector === 'undefined') ? '[data-session-control]' : data.sessionControlQuerySelector;
     return () => {
        const sessionControllerElements = document.querySelectorAll(querySelector);
        for (let element of sessionControllerElements) {
            element.onclick = openWorkstationSession(element);
        }
    }
}

function sendSessionControlMessage(targetWindow, origin, action, ackCallback) {
    const msg = {
                sessionControl: {
                    header: {
                        id: UUIDv4()
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
        const ack = msg.header.acknowledge;
        if (!ack) {
            return
        }
        if (msg.header.id) {
            ackCallback();
            window.removeEventListener('message', checkAckMessage);
        }
    }
    window.addEventListener('message', checkAckMessage);
}

function UUIDv4() {
  return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
    (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
  );
}

let sessionControllersHook;
if (typeof sessionControllersHook === 'undefined') { // singleton
    sessionControllersHook = genSessionControllersHook();
}

$(document).ready(() => {
    // Run default once
    sessionControllersHook();

    // Sometimes content insertion is deferred and might result in adding session-control elements later:
    //  add listeners:

    // ajax-based tables
    $('#ajaxDataTable').on('draw.dt', () => {sessionControllersHook()});

    // htmx-based tables
    htmx.onLoad(function() {
        sessionControllersHook()
    });
});

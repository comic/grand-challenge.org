'use strict';

function openWorkstationSession(element) {
    return (event) => {
        const windowIdentifier = element.dataset.workstationWindowIdentifier;
        const url = element.dataset.createSessionUrl;
        const query = element.dataset.workstationQuery;
        const creationURI = `${url}?${query}`;
        const domain = element.dataset.domain;

        if (event.ctrlKey) {
            window.open(creationURI);
            return;
        }

        const regions = JSON.parse(document.getElementById('workstation-regions').textContent);
        const sessionOrigins = getSessionOrigins(domain, regions);

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
            for (let i = 0; i < sessionOrigins.length; i++) {
                const msg = {
                    sessionControl: {
                        // TODO unsure if a message id is really necessary, but if so, it should be a unique id and not just the session origin
                        messageId: sessionOrigins[i],
                    }
                }
                workstationWindow.postMessage(msg, sessionOrigins[i]);
            }

            let messageReceived = false;
            setTimeout(function() {
                if (!messageReceived) {
                    window.open(creationURI, windowIdentifier);
                }
            }, 3000);
            function receiveMessage(event) {
                if (sessionOrigins.includes(event.source.origin)) {
                    messageReceived = true;
                    // TODO check for messageID in event.data if we're including it in the message
                    workstationWindow.focus();
                    const msg = {
                        sessionControl: {
                            loadQuery: query,
                        }
                    }
                    workstationWindow.postMessage(msg, event.source.origin);
                }
            }

            window.addEventListener('message', receiveMessage);

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
})

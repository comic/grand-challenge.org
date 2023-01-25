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

        const workstationRegions = JSON.parse(document.getElementById('workstation-regions').textContent);
        let sessionOrigins = Array();
        for (let i = 0; i < workstationRegions.length; i++) {
            if (domain.includes("localhost")) {
                // for testing don't prepend regions
                sessionOrigins.push("https://" + domain);
            } else {
                sessionOrigins.push("https://" + workstationRegions[i] + "." + domain);
            }
        }

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
                        loadQuery: query,
                        messageId: sessionOrigins[i],
                    }
                }
                // TODO wait for response
                workstationWindow.postMessage(msg, sessionOrigin[i]);
            }
        }
    }
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

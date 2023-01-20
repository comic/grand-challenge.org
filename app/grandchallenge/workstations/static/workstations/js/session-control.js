'use strict';

function openWorkstationSession(element) {
    return (event) => {
        const windowIdentifier = element.dataset.workstationWindowIdentifier;
        const url = element.dataset.createSessionUrl;
        const query = element.dataset.workstationQuery;
        const creationURI = `${url}?${query}`;
        const sessionListUrl = element.dataset.sessionUrl;
        const domain = element.dataset.domain;

        if (event.ctrlKey) {
            window.open(creationURI);
            return;
        }

        let activeSessions;
        $.ajax({
            url: sessionListUrl,
            async: false,
            success: function(data){
                activeSessions = data;
            },
        });
        const region = processActiveSessions(activeSessions);

        let sessionOrigin;
        if (typeof region !== "undefined") {
            sessionOrigin = "https://" + region + "." + domain;
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

        if (workstationWindow === null || isBlankContext || typeof sessionOrigin === 'undefined' ) {
            window.open(creationURI, windowIdentifier);
        } else {
            workstationWindow.focus();
            const msg = {
                sessionControl: {
                    loadQuery: query
                }
            }
            // TODO wait for response
            workstationWindow.postMessage(msg, sessionOrigin);
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

function processActiveSessions(activeSessions) {
    if (activeSessions["count"] !== 0) {
        return activeSessions["results"][0]["region"];
    } else {
        return undefined;
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

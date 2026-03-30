function updateRequestConfig(event) {
    for (const [key, val] of Object.entries(event.detail.parameters)) {
        if (key.startsWith("interface")) {
            event.detail.parameters.interface = val;
            delete event.detail.parameters[key];
        }
    }
}

function processSelectElements() {
    const selectElements = document.querySelectorAll(
        'select[name^="interface"]',
    );
    for (const elem of selectElements) {
        const observer = new MutationObserver((mutationsList, observer) => {
            for (const mutation of mutationsList) {
                if (mutation.target === elem) {
                    elem.addEventListener(
                        "htmx:configRequest",
                        updateRequestConfig,
                    );
                    htmx.trigger(elem, "interfaceSelected");
                }
            }
        });
        observer.observe(elem, { childList: true });
    }
}

htmx.onLoad(elem => {
    processSelectElements();
    const dalForwardConfScripts = document.querySelectorAll(
        ".dal-forward-conf script",
    );

    // Forward unique interface slugs from label elements on the page
    const forwards = [];
    const interfaceFieldMarker = JSON.parse(
        document.getElementById("interfaceFormFieldPrefix").textContent,
    );
    const labels = document.querySelectorAll(
        `label[for*="${interfaceFieldMarker}"]`,
    );

    const uniqueInterfaceSlugs = [
        ...new Set(
            Array.from(labels).map(label => {
                const forAttr = label.htmlFor;
                const markerIndex = forAttr.indexOf(interfaceFieldMarker);
                const start = markerIndex + interfaceFieldMarker.length;
                return forAttr.slice(start);
            }),
        ),
    ];

    for (const interfaceSlug of uniqueInterfaceSlugs) {
        forwards.push({
            type: "const",
            dst: `interface_${interfaceSlug}`,
            val: interfaceSlug,
        });
    }

    const objectSlug = document.getElementById("objectSlug").dataset.objectSlug;
    const modelName = document.getElementById("modelName").dataset.modelName;
    forwards.push({
        type: "const",
        dst: "object_slug",
        val: objectSlug,
    });
    forwards.push({
        type: "const",
        dst: "model_name",
        val: modelName,
    });

    const config = JSON.stringify(forwards);
    for (const script of dalForwardConfScripts) {
        script.textContent = config;
    }
});

processSelectElements();

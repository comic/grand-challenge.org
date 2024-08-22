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
    selectElements.forEach(elem => {
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
    });
}

htmx.onLoad(elem => {
    processSelectElements();
    const dalForwardConfScripts = document.querySelectorAll(
        ".dal-forward-conf script",
    );
    dalForwardConfScripts.forEach(script => (script.textContent = ""));
    let vals = [];
    const selectOptions = document.querySelectorAll(
        'select:disabled[name^="interface"] option:checked',
    );
    selectOptions.forEach(option => {
        vals.push(option.value);
    });

    if (vals.length) {
        vals = vals.map(
            val =>
                `{"type": "const", "dst": "interface-${val}", "val": "${val}"}`,
        );
    }

    const objectSlugVal = document.getElementById("objectSlug").dataset.slug;
    const objectModel = document.getElementById("modelName").dataset.modelName;
    vals.push(
        `{"type": "const", "dst": "object", "val": "${objectSlugVal}"}`,
        `{"type": "const", "dst": "model", "val": "${objectModel}"}`,
    );

    dalForwardConfScripts.forEach(
        script => (script.textContent = `[${vals.join(",")}]`),
    );
});

processSelectElements();

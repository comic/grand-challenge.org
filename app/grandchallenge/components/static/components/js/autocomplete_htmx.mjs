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
    for (const script of dalForwardConfScripts) {
        script.textContent = "";
    }
    let vals = [];
    const selectOptions = document.querySelectorAll(
        'select:disabled[name^="interface"] option:checked',
    );
    for (const option of selectOptions) {
        vals.push(option.value);
    }

    if (vals.length) {
        vals = vals.map(
            val =>
                `{"type": "const", "dst": "interface-${val}", "val": "${val}"}`,
        );
    }

    const objectSlug = document.getElementById("objectSlug").dataset.objectSlug;
    const modelName = document.getElementById("modelName").dataset.modelName;
    vals.push(
        `{"type": "const", "dst": "object_slug", "val": "${objectSlug}"}`,
        `{"type": "const", "dst": "model_name", "val": "${modelName}"}`,
    );

    for (const script of dalForwardConfScripts) {
        script.textContent = `[${vals.join(", ")}]`;
    }
});

processSelectElements();

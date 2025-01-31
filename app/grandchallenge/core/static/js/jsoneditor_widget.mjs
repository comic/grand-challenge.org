function initialize_jsoneditor_widget(jsoneditorWidgetID) {
    const schema = JSON.parse(
        document.getElementById(`schema_${jsoneditorWidgetID}`).textContent,
    );
    const container = document.getElementById(
        `jsoneditor_${jsoneditorWidgetID}`,
    );
    const jsoneditorWidget = document.getElementById(jsoneditorWidgetID);
    const feedback = document.getElementById(
        `jsoneditor_feedback_${jsoneditorWidgetID}`,
    );

    let validityErrors = false;

    if (jsoneditorWidget.disabled) {
        jsoneditorWidget.classList.remove("d-none");
    } else {
        const options = {
            mode: "tree",
            modes: ["code", "tree"],
            allowSchemaSuggestions: true,
            showErrorTable: ["code"],
            onChangeText: jsonString => {
                jsoneditorWidget.value = jsonString;
            },
            onValidationError: errors => {
                validityErrors = errors.length > 0;
            },
        };

        if (schema !== undefined) {
            options.schema = schema;
        }

        const editor = new JSONEditor(container, options);

        let data;
        try {
            data = JSON.parse(jsoneditorWidget.value);
        } catch (err) {
            console.warn(
                "Could not parse JSON data:",
                jsoneditorWidget.value,
                err,
            );
        }

        if (typeof data !== "undefined") {
            editor.set(data);
            editor.expandAll();
        }

        function handleSubmitEvent(e) {
            if (validityErrors) {
                e.preventDefault();
                feedback.innerHTML = "<strong>Invalid JSON</strong>";
                container.scrollIntoView();
                editor.focus();
            } else {
                feedback.innerText = "";
            }
        }

        jsoneditorWidget.form.addEventListener("submit", handleSubmitEvent);
        jsoneditorWidget.form.addEventListener("htmx:beforeRequest", e => {
            // Event might not be fired by form, so check.
            if (e.srcElement === jsoneditorWidget.form && validityErrors) {
                e.preventDefault(); // Prevent htmx request
            }
        });
    }
}

function search_for_jsoneditor_widgets(elem) {
    let jsoneditorWidgets;
    if (elem === undefined) {
        jsoneditorWidgets = document.getElementsByClassName("jsoneditorWidget");
    } else {
        jsoneditorWidgets = elem.getElementsByClassName("jsoneditorWidget");
    }
    for (const jsoneditorWidget of jsoneditorWidgets) {
        if (jsoneditorWidget.querySelector(".jsoneditor-mode-tree") === null) {
            // only initialize the widget if it hasn't been initialized yet
            initialize_jsoneditor_widget(jsoneditorWidget.dataset.widgetId);
        }
    }
}

document.addEventListener("DOMContentLoaded", event => {
    htmx.onLoad(elem => {
        search_for_jsoneditor_widgets(elem);
    });
});

// this is necessary for when an invalid form is returned through htmx (e.g. in display set views)
if (typeof htmx !== "undefined") {
    htmx.onLoad(elem => {
        if (elem.tagName.toLowerCase() === "body") {
            search_for_jsoneditor_widgets(elem);
        }
    });
}
search_for_jsoneditor_widgets();

function initialize_jsoneditor_widget(jsoneditorWidgetID) {
    const schema = JSON.parse(
        document.getElementById(`schema_${jsoneditorWidgetID}`).textContent,
    );
    const container = document.getElementById(
        `jsoneditor_${jsoneditorWidgetID}`,
    );
    const jsoneditorWidget = document.getElementById(jsoneditorWidgetID);

    if (jsoneditorWidget.disabled) {
        jsoneditorWidget.classList.remove("d-none");
    } else {
        const options = {
            mode: "tree",
            modes: ["code", "tree"],
            onChangeText: jsonString => {
                const widget = document.getElementById(jsoneditorWidgetID);
                try {
                    JSON.parse(jsonString);
                    widget.value = jsonString;
                    widget.setCustomValidity("");
                } catch (err) {
                    widget.setCustomValidity("JSON is invalid");
                }
            },
        };

        const editor = new JSONEditor(container, options);

        editor.set(
            JSON.parse(document.getElementById(jsoneditorWidgetID).value),
        );
        editor.expandAll();

        if (schema !== undefined) {
            editor.setSchema(schema);
        }
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

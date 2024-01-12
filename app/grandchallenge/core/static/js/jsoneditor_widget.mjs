function initialize_jsoneditor_widget(jsoneditorWidgetID) {
    const schema = JSON.parse(document.getElementById(`schema_${jsoneditorWidgetID}`).textContent)
    const container = document.getElementById(`jsoneditor_${jsoneditorWidgetID}`);
    const options = {
        mode: 'tree',
        modes: ['code', 'tree'],
        onChangeText: function (jsonString) {
            let widget = document.getElementById(jsoneditorWidgetID)
            try {
                JSON.parse(jsonString);
                widget.value = jsonString;
                widget.setCustomValidity("");
            } catch (err) {
                widget.setCustomValidity("JSON is invalid");
            }
        }
    };

    let editor = new JSONEditor(container, options);

    editor.set(JSON.parse(document.getElementById(jsoneditorWidgetID).value));
    editor.expandAll();

    if (schema !== undefined) {
        editor.setSchema(schema);
    }
}

function search_for_jsoneditor_widgets(elem) {
    let jsoneditorWidgets;
    if (elem === undefined) {
        jsoneditorWidgets = document.getElementsByClassName("jsoneditorWidget");
    } else {
        jsoneditorWidgets = elem.getElementsByClassName("jsoneditorWidget");
    }

    for (let jsoneditorWidget of jsoneditorWidgets) {
        initialize_jsoneditor_widget(jsoneditorWidget.dataset.widgetId);
    }
}

document.addEventListener("DOMContentLoaded", function(event) {
    search_for_jsoneditor_widgets()
});

htmx.onLoad((elem) => {
    search_for_jsoneditor_widgets(elem)
});

search_for_jsoneditor_widgets();
const form = document.getElementById('obj-form');
if (form !== undefined) {
   const observer = new MutationObserver(function(mutationsList, observer) {
        for(let mutation of mutationsList) {
           if (mutation.target === form) {
              search_for_jsoneditor_widgets();
           }
        }
   });
   observer.observe(form, {childList: true, subtree: true, attributes: true, attributeFilter: ['is-invalid']});
}

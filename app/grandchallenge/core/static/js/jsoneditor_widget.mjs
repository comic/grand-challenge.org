function initialize_jsoneditor_widget(jsoneditorWidgetID) {
    const schemaID = `schema_${jsoneditorWidgetID}`
    const schema = JSON.parse(document.getElementById(schemaID).textContent)
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

$(document).ready(function () {
    const jsoneditorWidgets = document.getElementsByClassName("jsoneditorWidget");

    for (let jsoneditorWidget of jsoneditorWidgets) {
        initialize_jsoneditor_widget(jsoneditorWidget.dataset.widgetId);
    }
})

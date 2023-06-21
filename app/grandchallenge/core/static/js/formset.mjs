const formsetPrefix = JSON.parse(document.getElementById("formsetPrefix").textContent)

$(`.formset_row-${formsetPrefix}`).formset({
    addText: 'Add another',
    deleteText: 'Remove',
    prefix: formsetPrefix,
    addCssClass: "btn btn-primary my-2",
    deleteCssClass: "btn btn-danger delete-row mb-2",
    hideLastAddForm: true,
});

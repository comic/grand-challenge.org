$(document).ready(() => {
    $("#methodsTable").DataTable({
        columnDefs: [
            {
                targets: "nonSortable",
                searchable: false,
                orderable: false,
            },
        ],
    });
});

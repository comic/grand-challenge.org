$(document).ready(function () {
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

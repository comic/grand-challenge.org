$(document).ready(() => {
    $("#groundtruthsTable").DataTable({
        columnDefs: [
            {
                targets: "nonSortable",
                searchable: false,
                orderable: false,
            },
        ],
    });
});

document.addEventListener("DOMContentLoaded", event => {
    $("#phaseCostsOverviewTable").DataTable({
        order: [[0, "asc"]],
        lengthChange: false,
        pageLength: 100,
        columnDefs: [
            {
                targets: "datatables-non-sortable",
                searchable: false,
                orderable: false,
            },
        ],
    });
});

document.addEventListener("DOMContentLoaded", event => {
    $("#challengeRequestsTable").DataTable({
        order: [[3, "desc"]],
        lengthChange: false,
        pageLength: 50,
        columnDefs: [
            {
                targets: "datatables-non-sortable",
                searchable: false,
                orderable: false,
            },
        ],
    });
});

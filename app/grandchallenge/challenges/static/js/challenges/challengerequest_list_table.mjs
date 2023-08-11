document.addEventListener("DOMContentLoaded", function(event) {
    $('#challengeRequestsTable').DataTable({
        order: [[3, "asc"]],
        lengthChange: false,
        pageLength: 50,
        columnDefs: [
            {
                targets: 'datatables-non-sortable',
                searchable: false,
                orderable: false,
            }
        ],
    });
});

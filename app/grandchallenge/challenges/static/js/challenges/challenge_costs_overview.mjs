document.addEventListener("DOMContentLoaded", function(event) {
    $('#challengeCostsOverviewTable').DataTable({
        order: [[2, "desc"]],
        lengthChange: false,
        pageLength: 100,
        columnDefs: [
            {
                targets: 'datatables-non-sortable',
                searchable: false,
                orderable: false,
            }
        ],
    });
});

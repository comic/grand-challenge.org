$(document).ready(() => {
    $("#pagesTable").DataTable({
        pageLength: 10,
        columnDefs: [
            {
                targets: [4, 5],
                searchable: false,
                orderable: false,
            },
        ],
    });
});

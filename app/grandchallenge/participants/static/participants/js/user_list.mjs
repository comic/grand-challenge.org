$(document).ready(() => {
    $("#usersTable").DataTable({
        pageLength: 10,
        columnDefs: [
            {
                targets: [-1],
                searchable: false,
                orderable: false,
            },
        ],
    });
});

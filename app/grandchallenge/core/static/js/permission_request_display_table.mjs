$(document).ready(function () {
    $('#usersTable').DataTable({
        order: [[7, "asc"], [0, "desc"]],
        "pageLength": 25,
        "columnDefs": [{
            "targets": [-1],
            "searchable": false,
            "orderable": false
        }]
    });
});

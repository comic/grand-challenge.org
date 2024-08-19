$(document).ready(function () {
    $('#usersTable').DataTable({
        "pageLength": 25,
    });

    $('#submissionsTable').DataTable({
        order: [[0, "desc"],],
        "pageLength": 25,
    });
});

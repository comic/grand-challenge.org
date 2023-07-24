$(document).ready(function () {
    $('#submissionsTable').DataTable({
        order: [[0, "desc"],],
        "pageLength": 100,
    });
});

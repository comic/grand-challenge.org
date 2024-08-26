$(document).ready(() => {
    $("#submissionsTable").DataTable({
        order: [[0, "desc"]],
        pageLength: 100,
    });
});

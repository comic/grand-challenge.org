$(document).ready(() => {
    $("#usersTable").DataTable({
        pageLength: 25,
    });

    $("#submissionsTable").DataTable({
        order: [[0, "desc"]],
        pageLength: 25,
    });
});

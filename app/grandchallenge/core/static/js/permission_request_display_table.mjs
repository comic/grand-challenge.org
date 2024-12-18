$(document).ready(() => {
    $("#usersTable").DataTable({
        order: [
            [7, "asc"],
            [0, "desc"],
        ],
        pageLength: 25,
    });
});

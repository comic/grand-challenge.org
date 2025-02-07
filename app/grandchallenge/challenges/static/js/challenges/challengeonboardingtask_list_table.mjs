$(document).ready(() => {
    $("#onboardingTasksTable").DataTable({
        order: [
            [0, "asc"],
            [5, "asc"],
        ],
        paging: false,
        info: false,
        searching: false,
    });
});

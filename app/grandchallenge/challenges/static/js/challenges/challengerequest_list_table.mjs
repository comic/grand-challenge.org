document.addEventListener("DOMContentLoaded", event => {
    $("#challengeRequestsTable").DataTable({
        order: [[3, "desc"]],
        lengthChange: false,
    });
});

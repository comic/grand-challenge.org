document.addEventListener("DOMContentLoaded", function(event) {
    $('#combinedRanksTable').DataTable({
        order: [[0, "asc"]],
        lengthChange: false,
        pageLength: 50,
    });
});

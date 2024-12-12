document.addEventListener("DOMContentLoaded", () => {
    $(".table").each(function () {
        $(this).DataTable({
            pageLength: 100,
            order: [[1, "asc"]],
        });
    });
});

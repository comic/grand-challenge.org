$(document).ready(() => {
    $(".table").each(function () {
        $(this).DataTable({
            pageLength: 100,
        });
    });
});

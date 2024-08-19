$(document).ready(function () {
    $('.table').each(function () {
        $(this).DataTable({
            pageLength: 100,
        });
    });
});

$(window).resize(function () {
    $('.table').each(function () {
        $(this).DataTable().columns.adjust();
    });
});

const defaultSortColumn = JSON.parse(document.getElementById("defaultSortColumn").textContent)

$(document).ready(function () {
    $('#ajaxDataTable').DataTable({
        order: [[defaultSortColumn, "desc"]],
        lengthChange: false,
        pageLength: 25,
        serverSide: true,
        ajax: {
            url: "",
        },
        ordering: true,
    });
});

$(window).resize(function () {
    $('#ajaxDataTable').DataTable().columns.adjust()
})

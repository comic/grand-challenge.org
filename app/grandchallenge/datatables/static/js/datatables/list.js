const defaultSortColumn = JSON.parse(document.getElementById("defaultSortColumn").textContent)

$(document).ready(function () {
    $('#ajaxDataTable').DataTable({
        order: [[defaultSortColumn, "desc"]],
        lengthChange: false,
        pageLength: 25,
        serverSide: true,
        ajax: {
            url: "",
            dataSrc: function ( json ) {
                const table = $('#ajaxDataTable').DataTable();
                for (const [index, visible] of json.showColumns.entries()) {
                    table.column(index).visible(visible)
                }
                return json.data;
            }
        },
        ordering: true,
    });
});

$(window).resize(function () {
    $('#ajaxDataTable').DataTable().columns.adjust()
})

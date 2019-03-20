"use strict";

$(document).ready(function () {
    $('table.sortable').dataTable({
        "bJQueryUI": false,
        "sPaginationType": "full_numbers",
        "bPaginate": false,
        "bLengthChange": false,
        "bFilter": false,
        "bInfo": false,
        "bAutoWidth": false
    });
});

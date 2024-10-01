$(document).ready(() => {
    $("#evaluationsTable").DataTable({
        order: [[2, "desc"]],
        responsive: {
            details: {
                renderer: (api, rowIdx, columns) => {
                    const data = $.map(columns, (col, i) =>
                        col.hidden
                            ? `<tr data-dt-row="${col.rowIndex}" data-dt-column="${col.columnIndex}"><td class="font-weight-bold">${col.title}:</td> <td>${col.data}</td></tr>`
                            : "",
                    ).join("");

                    return data ? $("<table/>").append(data) : false;
                },
            },
        },
    });
});

const defaultSortColumn = JSON.parse(
  document.getElementById("defaultSortColumn").textContent,
);
const textAlign = JSON.parse(document.getElementById("textAlign").textContent);
const defaultSortOrder = JSON.parse(
  document.getElementById("defaultSortOrder").textContent,
);

$(document).ready(function () {
  $("#ajaxDataTable").DataTable({
    order: [[defaultSortColumn, defaultSortOrder]],
    lengthChange: false,
    pageLength: 25,
    serverSide: true,
    responsive: {
      details: {
        renderer: function (api, rowIdx, columns) {
          var data = $.map(columns, function (col, i) {
            return col.hidden
              ? '<tr data-dt-row="' +
                  col.rowIndex +
                  '" data-dt-column="' +
                  col.columnIndex +
                  '">' +
                  '<td class="font-weight-bold">' +
                  col.title +
                  ":" +
                  "</td> " +
                  "<td>" +
                  col.data +
                  "</td>" +
                  "</tr>"
              : "";
          }).join("");

          return data ? $("<table/>").append(data) : false;
        },
      },
    },
    columnDefs: [
      {
        targets: "nonSortable",
        searchable: false,
        orderable: false,
      },
      {
        className: `align-middle text-${textAlign}`,
        targets: "_all",
      },
    ],
    ajax: {
      url: "",
      dataSrc: function (json) {
        const table = $("#ajaxDataTable").DataTable();
        for (const [index, visible] of json.showColumns.entries()) {
          table.column(index).visible(visible);
        }
        return json.data;
      },
    },
    ordering: true,
  });
});

$("#ajaxDataTable").on("init.dt", function () {
  // This is a work-around to get the table to resize properly on extra-large Bootstrap viewport
  setTimeout($("#ajaxDataTable").DataTable().columns.adjust, 1000);
});

//
$(window).resize(function () {
  $("#ajaxDataTable").DataTable().columns.adjust();
});

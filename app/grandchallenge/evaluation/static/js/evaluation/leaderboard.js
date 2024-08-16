const allowMetricsToggling = JSON.parse(
  document.getElementById("allowMetricsToggling").textContent,
);
const displayLeaderboardDateButton = JSON.parse(
  document.getElementById("displayLeaderboardDateButton").textContent,
);

let resultsTable = $("#ajaxDataTable");

$(document).ready(function () {
  let table = resultsTable.DataTable({
    // The column index of the default sort, must match the table set up.
    order: [[0, "asc"]],
    lengthChange: false,
    pageLength: 50,
    serverSide: true,
    ajax: {
      url: "",
    },
    columnDefs: [
      {
        targets: "nonSortable",
        searchable: false,
        orderable: false,
      },
      {
        targets: "toggleable",
        visible: false,
        orderable: false,
      },
    ],
    ordering: true,
    autoWidth: false,
    dom: getDataTablesDOMTemplate(),
    buttons: getDataTablesButtons(),
  });

  if (allowMetricsToggling === true) {
    resultsTable.on("column-visibility.dt", function () {
      let button = table.button(1).node();
      let visibility_columns = table.columns(".toggleable").visible();
      let not_all_visible = false;
      visibility_columns.each(function (value) {
        if (value === false) {
          not_all_visible = true;
          return false;
        }
      });
      if (!not_all_visible) {
        button.addClass("metrics-hidden");
        button.text("Hide additional metrics");
      } else {
        button.removeClass("metrics-hidden");
        button.text("Show all metrics");
      }
    });
  }

  if (displayLeaderboardDateButton === true) {
    document.getElementById("compare-buttons-group").innerHTML += `
            <button type="button" class="btn btn-secondary" data-toggle="modal" data-target="#leaderboardDateModal"
                    title="Leaderboard history">
                <i class="fas fa-history"></i>
            </button>
        `;
  }
});

$(window).resize(function () {
  resultsTable.DataTable().columns.adjust();
});

function getDataTablesDOMTemplate() {
  let DOM = "<'row'<'col-12'f>>";

  if (allowMetricsToggling === true || displayLeaderboardDateButton === true) {
    DOM += "<'row'<'#compare-buttons-group.col-md-6'><'col px-0 text-right'B>>";
  }

  DOM +=
    "<'row'<'col-12'tr>><'row'<'col-sm-12 col-md-5'i><'col-sm-12 col-md-7'p>>";
  return DOM;
}

function getDataTablesButtons() {
  if (allowMetricsToggling === true) {
    return [
      {
        extend: "colvis",
        text: "Additional metrics",
        columns: ".toggleable",
      },
      {
        text: "Show all metrics",
        action: function (e, dt, node) {
          if ($(node).hasClass("metrics-hidden")) {
            dt.columns(".toggleable").visible(false);
            $(node).removeClass("metrics-hidden");
            $(node).text("Show all metrics");
          } else {
            dt.columns(".toggleable").visible(true);
            $(node).addClass("metrics-hidden");
            $(node).text("Hide additional metrics");
          }
        },
      },
    ];
  } else {
    return [];
  }
}

$(document).ready(function () {
  $("#groundtruthsTable").DataTable({
    columnDefs: [
      {
        targets: "nonSortable",
        searchable: false,
        orderable: false,
      },
    ],
  });
});

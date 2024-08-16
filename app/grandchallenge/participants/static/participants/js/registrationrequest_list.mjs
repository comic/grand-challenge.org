$(document).ready(function () {
  $("#participantsTable").DataTable({
    order: [[0, "desc"]],
    pageLength: 10,
    columnDefs: [
      {
        targets: [-1],
        searchable: false,
        orderable: false,
      },
    ],
  });
});

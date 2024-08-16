let user;

$(document).ready(() => {
  $("#warningModal").on("show.bs.modal", function (event) {
    const button = $(event.relatedTarget);
    const modal = $(this);
    modal.find(".warning-text").text(button.data("warning"));
    modal.find(".modal-action").text(button.data("action"));
    $("#warningModalLabel").text(button.data("title"));
    user = button.data("user");
  });
  $("#proceed").on("click", (e) => {
    const target = $(e.currentTarget);
    htmx.ajax("POST", `${target.data("baseurl")}remove-answers/${user}/`, {
      values: { csrfmiddlewaretoken: target.data("csrf") },
      headers: {
        "X-CSRFToken": target.data("csrf"),
        "Content-Type": "application/json",
      },
    });
  });
});

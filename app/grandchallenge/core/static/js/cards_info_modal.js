$("#InfoModal").on("show.bs.modal", function (event) {
    const button = $(event.relatedTarget);
    const modal = $(this);
    modal.find(".modal-title").text(button.data("title"));
    modal.find(".modal-description").text(button.data("description"));
    modal.find(".modal-url").attr("href", button.data("absolute-url"));
    modal.find(".modal-url").text(button.data("absolute-url"));
});

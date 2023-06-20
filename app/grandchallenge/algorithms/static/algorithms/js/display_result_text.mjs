$('#resultInfoModal').on('show.bs.modal', function (event) {
    let button = $(event.relatedTarget);
    let modal = $(this);
    const json_element = document.getElementById(button.data('pk'));
    if (json_element) {
        // json_element is created with the json_script filter using data from job.rendered_result_text,
        // which has been passed through bleach and so safe to use with .html here.
        modal.find('.modal-job-output').html(JSON.parse(json_element.textContent));
    } else {
        modal.find('.modal-job-output').text(button.data('output'));
    }
    modal.find('.modal-title').text(button.data('title'));
    modal.find('#resultDetailLink').attr("href", `${button.data("pk")}/`);
})

function removeCase(event) {
    const url = event.currentTarget.dataset.displaySetUrl;
    $('#removeCase').data('case', url);
    $('#removeCaseModal').modal('show');
}

$('#ajaxDataTable').on('init.dt', function() {
   var removeButtons = document.querySelectorAll(".remove-display-set")
    removeButtons.forEach(function(elem) {
        elem.addEventListener("click", removeCase);
   });
});

$(document).ready(() => {
    $('#removeCase').on('click', (e) => {
        $.ajax({
            type: 'DELETE',
            url: $(e.currentTarget).data("case"),
            data: {csrfmiddlewaretoken: window.drf.csrfToken},
            headers: {
                'X-CSRFToken': window.drf.csrftoken,
                'Content-Type': 'application/json'
            },
            success: (response) => {
                window.location.replace(window.location.href);
            },
            error: (response) => {
                $('#removeCaseModal').modal('hide');
                $("#messages").append(
                   '<div class="alert alert-danger" id="form-error-message">' +
                     `${response.responseJSON.detail}` +
                     '<button type="button" class="close"' +
                     'data-dismiss="alert" aria-label="Close">' +
                     '<span aria-hidden="true">&times;</span>' +
                     '</button>' +
                   '</div>'
                )
            },
        })
    });
});

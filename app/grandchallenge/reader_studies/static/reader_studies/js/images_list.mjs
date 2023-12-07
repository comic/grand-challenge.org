function removeCase(event) {
    const url = event.target.dataset.displaySetUrl;
    $('#removeCase').data('case', url);
    $('#removeCaseModal').modal('show');
}

$('#ajaxDataTable').on( 'init.dt', function() {
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
            complete: (response) => {
                window.location.replace(window.location.href);
            }
        })
    });
});

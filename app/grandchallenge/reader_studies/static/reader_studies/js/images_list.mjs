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

    $(document).on('submit', '.ds-form', (e) => {
        e.preventDefault();
        const target = $(e.currentTarget);
        const formData = target.serialize();
        $.ajax({
            type: 'POST',
            url: target.attr("action"),
            data: formData,
            success: (response) => {
                const elem = target.data("hx-target");
                $(elem).html(response);
                htmx.process(elem);
            }
        })
    });

    // Trigger htmx ajax request here, because using hx- attributes does not work in html loaded by datatables.js
    // TODO: replace datatables.js with htmx?
    $(document).on('click', '.ds-htmx', (e) => {
        const target = $(e.currentTarget);
        if (!target.data("loaded")) {
            htmx.ajax('GET', target.data("hx-get"), {target: target.data("hx-target"), swap: target.data("hx-swap")});
            target.data("loaded", true);
        }
    });

    document.body.addEventListener("htmx:afterSwap", function(evt) {
        // Add the removeCase function to buttons swapped in by htmx
        for (let elm of evt.target.getElementsByClassName("remove-display-set")) {
            elm.addEventListener("click", removeCase);
        }
    });
});

document.addEventListener('DOMContentLoaded', () => {

  htmx.onLoad( function() {
    const removeFormButtons = document.querySelectorAll('.remove-form');
    for (const button of removeFormButtons) {
        button.addEventListener('click', (event) => {
          event.preventDefault();
          const form = event.currentTarget.closest("form.extra-interface-form");
          if (form) {
            form.remove();
          }
      });
      };
  });

});

// force client side field validation for extra interface form fields
// htmx post won't get sent otherwise
document.getElementById('obj-form').addEventListener('submit', function(event) {
    var extraInterfaceForms = document.getElementsByClassName('extra-interface-form');

    for (var i = 0; i < extraInterfaceForms.length; i++) {
        var form = extraInterfaceForms[i];

        if (!form.checkValidity()) {
            form.reportValidity();
            event.preventDefault();
        }
    }
});

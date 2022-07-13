$(document).ready(() => {
   $('#form-new-ds').on('submit', (e) => {
      e.preventDefault();
      const target = $(e.currentTarget);
      $(".is-invalid").removeClass("is-invalid");
      $(".invalid-feedback").remove();
      $("#form-error-message").remove();
      const formData = {};
      const interfaces = [];
      $.each($(target).serializeArray(), (i, entry) =>{
          formData[entry.name] = entry.value
      });
      $(".extra-interface-form").each(
          (i, interfaceForm) => {
              const data = {}
              $.each($(interfaceForm).serializeArray(), (i, entry) =>{
                  data[entry.name] = entry.value
              });
              interfaces.push(data)
          }
      )
      formData.new_interfaces = interfaces;
      $.ajax({
          type: 'POST',
          url:  target.attr("action"),
          data: JSON.stringify(formData),
          dataType: 'json',
          contentType: 'application/json',
          headers: {
              'X-CSRFToken': window.drf.csrfToken,
              'Content-Type': 'application/json'
          },
          success: (response) => {
              window.location.href = response.redirect;
          },
          error: (response) => {
              const errors = response.responseJSON;
              for (key in errors) {
                  if (parseInt(key) === NaN) {
                      input = $(`[name='${key}']`);
                      formGroup = input.parents(".form-group");
                      input.addClass("is-invalid");
                      formGroup.append(`<div class="invalid-feedback">${errors[key].join('; ')}</div>`);

                  } else {
                      form = $(`[name='interface'] option[value='${key}']:selected`).parents("form.extra-interface-form");
                      form.find("input[name='value']").addClass("is-invalid");
                      form.append(`<div class="invalid-feedback">${errors[key].join('; ')}</div>`);
                  }
              }
              $("#messages").append(
                  '<div class="alert alert-danger" id="form-error-message">' +
                      'Please correct the errors below.' +
                      '<button type="button" class="close"' +
                      'data-dismiss="alert" aria-label="Close">' +
                          '<span aria-hidden="true">&times;</span>' +
                      '</button>' +
                  '</div>'
              );
              $("#messages")[0].scrollIntoView();
          }
      })
  });
});

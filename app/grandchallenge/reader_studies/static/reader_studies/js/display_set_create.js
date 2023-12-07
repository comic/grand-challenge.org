$.fn.serializeAll = function () {
  const data = $(this).serializeArray();

  $(':disabled[name]', this).each(function () {
      data.push({ name: this.name, value: $(this).val() });
  });

  return data;
}

$(document).ready(() => {
  $(document).on('click', '.remove-form', (e) => {
    $(e.currentTarget).parents("form.extra-interface-form").remove();
  });

  htmx.onLoad((elem) => {
    $('form').not($("#ds-form")).each((i, form) => {
      const selected = $("option:selected", form);
      if (selected.val()) {
        $('form').not($("#ds-form")).each((_, _form) => {
          if (_form != form) {
            $(_form).find(`option[value='${selected.val()}']`).remove();
          }
        });
      }
    });
  });
  $('#ds-form').on('submit', (e) => {
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
              $.each($(interfaceForm).serializeAll(), (i, entry) =>{
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
              let message;
              if (response.status == 400) {
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
                message = 'Please correct the errors below.'
              } else message = 'Unexpected error.'
              $("#messages").append(
                  '<div class="alert alert-danger" id="form-error-message">' +
                      `${message}` +
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

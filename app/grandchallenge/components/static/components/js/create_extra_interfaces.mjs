function serializeAll(form) {
  const data = Array.from(new FormData(form), ([name, value]) => ({ name, value }));
  // Include disabled form elements
  Array.from(form.querySelectorAll(':disabled[name]')).forEach(element => {
    data.push({ name: element.name, value: element.value });
  });
  return data;
}

function clearErrorMessages() {
  document.querySelectorAll(".is-invalid").forEach(element => {
    element.classList.remove("is-invalid");
  });
  document.querySelectorAll(".invalid-feedback").forEach(element => {
    element.remove();
  });
  const formErrorMessage = document.getElementById("form-error-message");
  if (formErrorMessage) {
    formErrorMessage.remove();
  }
}

function getFormData(form) {
  const formData = {};
  new FormData(form).forEach((value, name) => {
    formData[name] = value;
  });
  return formData;
}

function getInterfacesData() {
  return Array.from(document.querySelectorAll(".extra-interface-form")).map(interfaceForm => {
    const data = {};
    serializeAll(interfaceForm).forEach(entry => {
      data[entry.name] = entry.value;
    });
    return data;
  });
}

function submitFormData(target, formData) {
    return fetch(target.action, {
      method: 'POST',
      body: JSON.stringify(formData),
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': window.drf.csrfToken,
      },
    })
    .then(response => {
      if (!response.ok) {
        throw response;
      }
      return response.json();
    });
  }

function handleSuccess(response) {
  window.location.href = response.redirect;
}

function handleErrors(response) {
    if (response.status === 400) {
      response.json().then(errors => {
          const keys = Object.keys(errors);
          for (let i = 0; i < keys.length; i++) {
            const key = keys[i];
            var input;
            var formGroup;
            if (isNaN(parseInt(key))) {
              input = document.querySelector(`[name='${key}']`);
              formGroup = input.closest(".form-group");
            } else {
              formGroup = document.querySelector(`[name='interface'] option[value='${key}']:checked`).closest("form.extra-interface-form");
              const div_id = 'div_' + formGroup.querySelector('[name^="interface"]').id.replace('interface', '');
              const interfaceName = formGroup.children[2].id.replace(div_id, '');
              input = document.querySelector(`[name='${interfaceName}']`);
              formGroup.classList.add("border-danger");
            }
            input.classList.add("is-invalid");
            formGroup.insertAdjacentHTML('beforeend', `<div class="invalid-feedback">${errors[key].join('; ')}</div>`);
          }
          var message = 'Please correct the errors below.';
          displayErrorMessage(message);
    });
  } else {
    var message = 'Unexpected error.';
    displayErrorMessage(message);
  }
}

function displayErrorMessage(message) {
  const messagesContainer = document.getElementById("messages");
  messagesContainer.insertAdjacentHTML(
    'beforeend',
    '<div class="alert alert-danger" id="form-error-message">' +
    `${message}` +
    '<button type="button" class="close"' +
    'data-dismiss="alert" aria-label="Close">' +
    '<span aria-hidden="true">&times;</span>' +
    '</button>' +
    '</div>'
  );
  messagesContainer.scrollIntoView();
}

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

  document.getElementById('obj-form').addEventListener('submit', (event) => {
      event.preventDefault();
      clearErrorMessages();

      const form = event.currentTarget;
      const formData = getFormData(form);
      const interfaces = getInterfacesData();
      formData.new_interfaces = interfaces;

      submitFormData(form, formData)
      .then(handleSuccess)
      .catch(handleErrors);
});
});

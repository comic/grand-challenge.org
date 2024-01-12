function serializeAll(form) {
  const data = Array.from(new FormData(form), ([name, value]) => ({ name, value }));
  // Include disabled form elements
  Array.from(form.querySelectorAll(':disabled[name]')).forEach(element => {
    data.push({ name: element.name, value: element.value });
  });
  return data;
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
      if (entry.name.startsWith('interface')) {
        data['interface'] = entry.value;
      } else {
        data[entry.name] = entry.value;
      }
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
        'Accept': 'text/html'
      },
    })
    .then(response => {
      if (!response.redirected) {
        throw response;
      }
      return response;
    });
  }

function handleSuccess(response) {
    window.location.href = response.url;
}

function handleErrors(response) {
    response.text()
      .then(text => {
        let parser = new DOMParser();
	    let doc = parser.parseFromString(text, 'text/html');
	    let oldForm = document.getElementById('obj-form');
	    let formWithErrors = doc.getElementById('obj-form');
	    oldForm.innerHTML = formWithErrors.innerHTML;
	    htmx.process(oldForm);
        displayErrorMessage('Please correct the errors below.');
      })
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

      const form = event.currentTarget;
      const formData = getFormData(form);
      const interfaces = getInterfacesData();
      formData.new_interfaces = interfaces;

      submitFormData(form, formData)
      .then(handleSuccess)
      .catch(handleErrors);
});
});

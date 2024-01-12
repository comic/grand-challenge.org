$(document).ready(() => {
  $(".dal-forward-conf script").text("");

  $(document).on('change', 'select', (e) => {
    e.currentTarget.addEventListener("htmx:configRequest", updateRequestConfig);
    htmx.trigger(e.currentTarget, 'interfaceSelected');
  });

  htmx.onLoad((elem) => {
    let vals = [];
    $("select:disabled[name^='interface'] option:selected").each((i, option) => {
      vals.push($(option).val());
    });
    if (vals.length) {
      vals = vals.map(val => `{"type": "const", "dst": "interface-${val}", "val": "${val}"}`);
    }
    vals.push(`{"type": "const", "dst": "object", "val": "${$('#objectSlug').data('slug')}"}`);
    $(".dal-forward-conf script").text(`[${vals.join(',')}]`);
  });

});

function updateRequestConfig (event) {
    for (const [key, val] of Object.entries(event.detail.parameters)) {
        if (key.startsWith('interface')) {
            event.detail.parameters['interface'] = val
            delete event.detail.parameters[key]
        }
    }
}

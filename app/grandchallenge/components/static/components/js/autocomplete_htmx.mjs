$(document).ready(() => {
  $(".dal-forward-conf script").text("");

  $(document).on('change', 'select', (e) => {
    htmx.trigger(e.currentTarget, 'interfaceSelected');
  });

  htmx.onLoad((elem) => {
    let vals = [];
    $("select:disabled[name='interface'] option:selected").each((i, option) => {
      vals.push($(option).val());
    });
    if (vals.length) {
      vals = vals.map(val => `{"type": "const", "dst": "interface-${val}", "val": "${val}"}`);
    }
    vals.push(`{"type": "const", "dst": "object", "val": "${$('#objectSlug').data('slug')}"}`);
    $(".dal-forward-conf script").text(`[${vals.join(',')}]`);
  });

});

$(document).ready(() => {
  $(".dal-forward-conf script").text("");

  $(document).on('change', 'select', (e) => {
    const val = yl.getValueFromField(e.currentTarget);
    $(e.currentTarget).find('option').attr('selected', false);
    $(e.currentTarget).find(`option[value='${val}']`).attr("selected", true);
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
    vals.push(`{"type": "const", "dst": "reader-study", "val": "${$('#readerStudySlug').data('slug')}"}`);
    $(".dal-forward-conf script").text(`[${vals.join(',')}]`);
  });

});

$('#ajaxDataTable').on( 'init.dt', function() {
   var allSelectElements = document.querySelectorAll('[id^="interfaceSelect"]');
   allSelectElements.forEach(function(elem) {
        elem.addEventListener("change", loadUpdateView);
   });
});

function loadUpdateView(source) {
    window.location.href = source.target.value
}

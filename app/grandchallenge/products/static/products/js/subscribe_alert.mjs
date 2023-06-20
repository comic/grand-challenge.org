$(window).on('load', function () {
    if (!sessionStorage.getItem('shown-alert')) {
        $('#subscribeAlert').show();
        sessionStorage.setItem('shown-alert', 'true');
    }
});

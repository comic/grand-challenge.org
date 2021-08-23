window.toggleCheckboxes = function toggleCheckboxes(source) {
    $('input[name="checkbox"]').each(function () {
        this.checked = source.checked;
    })
    const nChecked = $('input[name="checkbox"]:checked').length
    if (nChecked == 0) {
        document.getElementById('LabelSelectAll').innerHTML = 'Select all'
    } else {
        document.getElementById('LabelSelectAll').innerHTML = nChecked + ' selected'
    }
}

function sendAjaxCall(type, data) {
    let arrayOfPromises = [];
        $('input[name="checkbox"]:checked').each(function () {
            if ($(this).data('flag') == 'job-follow') {
                arrayOfPromises.push($.ajax({
                    type: 'PATCH',
                    url: $(this).data('url'),
                    data: JSON.stringify({flag: "job-inactive"}),
                    contentType: 'application/json',
                    accept: 'application/json',
                }))
            } else {
                arrayOfPromises.push($.ajax({
                    type: type,
                    url: $(this).data('url'),
                    data: JSON.stringify(data),
                    contentType: 'application/json',
                    accept: 'application/json',
                }))
            }
        })
        Promise.all(arrayOfPromises).then(function () {
            window.location.replace(window.location.href);
        });
}

$(document).ready(() => {
    $('#delete').on('click', () => {
        sendAjaxCall('DELETE', {})
    });
    $('#mark_read').on('click', () => {
        sendAjaxCall('PATCH', {read: true})
    });
    $('#mark_unread').on('click', () => {
        sendAjaxCall('PATCH', {read: false})
    });
});

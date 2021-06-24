function toggleCheckboxes(source) {
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

$(document).ready(() => {
    $('#delete').on('click', () => {
        let arrayOfPromises = [];
        $('input[name="checkbox"]:checked').each(function () {
            arrayOfPromises.push($.ajax({
                type: 'DELETE',
                url: $(this).data('url'),
                data: {},
                contentType: 'application/json',
                accept: 'application/json',
            }))
        })
        Promise.all(arrayOfPromises).then(function () {
            window.location.replace(window.location.href);
        });
    });
    $('#mark_read').on('click', () => {
        let arrayOfPromises = [];
        $('input[name="checkbox"]:checked').each(function () {
            arrayOfPromises.push($.ajax({
                type: 'PATCH',
                url: $(this).data('url'),
                data: JSON.stringify({read: true}),
                contentType: 'application/json',
                accept: 'application/json',
            }))
        })
        Promise.all(arrayOfPromises).then(function () {
            window.location.replace(window.location.href);
        })
    });
    $('#mark_unread').on('click', () => {
        let arrayOfPromises = [];
        $('input[name="checkbox"]:checked').each(function () {
            arrayOfPromises.push($.ajax({
                type: 'PATCH',
                url: $(this).data('url'),
                data: JSON.stringify({read: false}),
                contentType: 'application/json',
                accept: 'application/json',
            }))
        })
        Promise.all(arrayOfPromises).then(function () {
            window.location.replace(window.location.href);
        });
    });
});

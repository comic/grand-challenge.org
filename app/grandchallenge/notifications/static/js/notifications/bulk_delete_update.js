function toggleCheckboxes(source) {
    let checkboxes = document.getElementsByName('checkbox');
    for (let i = 0, n = checkboxes.length; i < n; i++) {
        checkboxes[i].checked = source.checked;
    }
    let n_checked = $('input[name="checkbox"]:checked').length
    if (n_checked == 0) {
        document.getElementById('LabelSelectAll').innerHTML = 'Select all'
    } else {
        document.getElementById('LabelSelectAll').innerHTML = n_checked + ' selected'
    }
    $('input[name="checkbox"]:checked').each(function () {
        console.log($(this).data('url'))
    })
}

$(document).ready(() => {
    $('#delete').on('click', () => {
        let arrayOfPromises = [];
        $('input[name="checkbox"]:checked').each(function (e) {
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
        $('input[name="checkbox"]:checked').each(function (e) {
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
        $('input[name="checkbox"]:checked').each(function (e) {
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

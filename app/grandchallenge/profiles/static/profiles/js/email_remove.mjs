const emailConfirmMessage = JSON.parse(document.getElementById('emailConfirmMessage').textContent);

(function () {
    let message = emailConfirmMessage;
    let actions = document.getElementsByName('action_remove');
    if (actions.length) {
        actions[0].addEventListener("click", function (e) {
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    }
})();

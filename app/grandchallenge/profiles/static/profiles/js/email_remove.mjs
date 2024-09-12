const emailConfirmMessage = JSON.parse(
    document.getElementById("emailConfirmMessage").textContent,
);
(() => {
    const message = emailConfirmMessage;
    const actions = document.getElementsByName("action_remove");
    if (actions.length) {
        actions[0].addEventListener("click", e => {
            if (!confirm(message)) {
                e.preventDefault();
            }
        });
    }
})();

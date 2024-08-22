$(document).ready(() => {
    const formsetPrefix = JSON.parse(
        document.getElementById("formsetPrefix").textContent,
    );
    const emptyForm = document.getElementById(
        `empty-form-${formsetPrefix}`,
    ).innerHTML;
    const addButton = document.getElementById(`add-form-row-${formsetPrefix}`);
    const totalForms = document.getElementById(
        `id_${formsetPrefix}-TOTAL_FORMS`,
    );

    addButton.addEventListener("click", addFormRow);

    function addFormRow(e) {
        e.preventDefault();

        const formNum = Number.parseInt(totalForms.value) + 1;
        const newForm = emptyForm.replace(/__prefix__/g, totalForms.value);
        addButton.insertAdjacentHTML("beforebegin", newForm);
        totalForms.setAttribute("value", formNum);
    }
});

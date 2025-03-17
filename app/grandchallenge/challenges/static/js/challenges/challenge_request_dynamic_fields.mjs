function updateExtraField(fieldName, helpText) {
    const checkboxFieldId = `id_${fieldName}`;
    const extraFieldDiv = `div_id_${fieldName}_extra`;
    const extraFieldId = `id_${fieldName}_extra`;
    const checkbox = document.getElementById(checkboxFieldId);
    if (checkbox.checked) {
        document.getElementById(extraFieldDiv).style.display = "none";
        document.getElementById(extraFieldId).required = false;
    } else {
        document.getElementById(extraFieldDiv).style.display = "block";
        document.getElementById(extraFieldId).required = true;
        document
            .getElementById(extraFieldDiv)
            .querySelector(
                "label",
            ).innerHTML = `Why are you not willing/able to ${helpText}? *`;
    }
}

document.addEventListener("DOMContentLoaded", () => {
    const dataLicenseCheckbox = document.getElementById("id_data_license");

    dataLicenseCheckbox.addEventListener("change", () => {
        updateExtraField("data_license", "use a CC-BY license for your data");
    });

    updateExtraField("data_license", "use a CC-BY license for your data");
});

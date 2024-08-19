function updateExtraField(fieldName, helpText) {
    let checkboxFieldId = "id_" + fieldName;
    let extraFieldDiv = "div_id_" + fieldName + "_extra";
    let extraFieldId = "id_" + fieldName + "_extra";
    let checkbox = document.getElementById(checkboxFieldId);
    if (checkbox.checked) {
        document.getElementById(extraFieldDiv).style.display = "none";
        document.getElementById(extraFieldId).required = false;
    } else {
        document.getElementById(extraFieldDiv).style.display = "block";
        document.getElementById(extraFieldId).required = true;
        document
            .getElementById(extraFieldDiv)
            .querySelector("label").innerHTML =
            "Why are you not willing/able to " + helpText + "? *";
    }
}

$(document).ready(function () {
    updateExtraField(
        "long_term_commitment",
        "support this challenge long-term",
    );
    updateExtraField("data_license", "use a CC-BY license for your data");
});

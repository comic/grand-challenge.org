$(document).ready(() => {
    const toggleOptions = () => {
        $(".options-formset").toggleClass('d-none', ["CHOI", "MCHO", "MCHD"].indexOf($("#id_answer_type").val()) === -1);
    }
    toggleOptions();
    $("#id_answer_type").on("change", () => {
        toggleOptions();
    });
});

$(document).ready(() => {
    const toggleOptions = () => {
        $(".options-formset").toggleClass(
            "d-none",
            ["CHOI", "MCHO"].indexOf($("#id_answer_type").val()) === -1,
        );
    };
    toggleOptions();
    $("#id_answer_type").on("change", () => {
        toggleOptions();
    });
});

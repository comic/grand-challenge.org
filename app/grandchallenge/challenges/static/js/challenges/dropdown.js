$("#leaderboardPhaseNavTrigger").click(e => {
    e.stopPropagation();
    $("#leaderboardPhaseNavDropdown").dropdown("toggle");
});
$("#submissionPhaseNavTrigger").click(e => {
    e.stopPropagation();
    $("#submissionPhaseNavDropdown").dropdown("toggle");
});

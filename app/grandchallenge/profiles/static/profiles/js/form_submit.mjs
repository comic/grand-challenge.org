document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("unsubscribeForm");
  if (form.classList.contains("auto-submit")) {
    form.submit();
  }
});

if (window.location.hash == "" || window.location.hash == '#information') {
  $('#information').addClass('active');
  $('#v-pills-information-tab').addClass('active');
}

$('#v-pills-tab a').click(function () {
  $(this).siblings().removeClass('active');
  $(this).tab('active');
});

// store the currently selected tab in the hash value
$("ul.nav-pills > a").on("shown.bs.tab", function (e) {
  const id = $(e.target).attr("href").substr(1);
  window.location.hash = id;
});

// on load of the page: switch to the currently selected tab
const hash = window.location.hash;
$('#v-pills-tab a[href="' + hash + '"]').siblings().removeClass('active');
$('#v-pills-tab a[href="' + hash + '"]').tab('show');

if (window.location.hash === "" || window.location.hash === '#information') {
  $('#information').addClass('active');
  $('#v-pills-information-tab').addClass('active');
}

$('#v-pills-tab a').click(function () {
  const tab = $(this);
  tab.siblings().removeClass('active');
  tab.tab('show');
});

// store the currently selected tab in the hash value
$("ul.nav-pills > a").on("shown.bs.tab", (e) => {
  const href = $(e.target).attr("href");
  const newUrl = new URL(href, window.location);
  history.pushState(null, null, newUrl.hash);
});

function activateLocation() {
  const hash = encodeURIComponent(window.location.hash.substring(1));
  const tab = $(`#v-pills-tab a[href="#${hash}"]`);
  tab.siblings().removeClass('active');
  tab.tab('show');
}

window.addEventListener('popstate', function (event) {
  activateLocation();
});

activateLocation();

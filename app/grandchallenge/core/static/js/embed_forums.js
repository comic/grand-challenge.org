"use strict";

$(document).ready(function () {
    var forum = document.getElementById('forum_embed');
    if (forum) {
        try {
            forum.src = 'https://groups.google.com/forum/embed/?place=forum/'
                + forum.dataset['groupname']
                + '&showsearch=true&showpopout=true&showtabs=false'
                + '&parenturl=' + encodeURIComponent(window.location.href);
        } catch (e) {
            console.log(e);
        }
    }
});

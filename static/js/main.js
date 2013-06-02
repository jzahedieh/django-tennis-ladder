var pathname = window.location.pathname;

$(document).ready(function() {
    var links = $(".nav li");
    $(links).each(function() {
        if($(this).children("a").attr("href") == pathname) {
            $(this).addClass("active");
        }
    });
});

function validateForm(formName, required) {
    var invalid = [];
    required.forEach(function(fieldName) {
        var x = document.forms[formName][fieldName].value;
        if (x == null || x == "") {
            invalid.push(fieldName);
        }
    });
    if (invalid.length > 0) {
        alert("Required fields are empty: " + invalid.join(', '));
        return false;
    }
}

function stripSpace(str) {
    return str.replace(/ /g, '');
}

/* http://stackoverflow.com/questions/1539367/remove-whitespace-and-line-breaks-between-html-elements-using-jquery */
jQuery.fn.cleanWhitespace = function() {
    textNodes = this.contents().filter(
        function() { return (this.nodeType == 3 && !/\S/.test(this.nodeValue)); })
        .remove();
    return this;
}

$( document ).ready(function() {
    $('.sections h3').each(function () {
        if ( ! this.id || this.id === "") {
            this.id = stripSpace(this.innerHTML);
        }
    });

    /* display: inline-block doesn't play nicely with whitespace ... */
    $('#party-links').cleanWhitespace();

    $('.party-figure').click(function() {
        var target = $('#' + stripSpace($(this).attr('title')));
        var old_background = jQuery.Color(target, 'background-color');
        var header = $('.header');
        $('html, body').animate({
            scrollTop: target.offset().top - header.height()
        }, 500);
        target.css('background-color', jQuery.Color(header, 'background-color'))
            .delay(1000)
            .animate({
                backgroundColor: old_background
            }, 1000);
    });
});


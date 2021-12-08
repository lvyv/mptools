var mxBasePath = '../../src';
var urlParams = (function () {
    var result = new Object();
    var params = window.location.search.slice(1).split('&');

    for (var i = 0; i < params.length; i++) {
        idx = params[i].indexOf('=');

        if (idx > 0) {
            result[params[i].substring(0, idx)] = params[i].substring(idx + 1);
        }
    }
    return result;
})(window.location.href);
var mxLanguage = urlParams['lang'];
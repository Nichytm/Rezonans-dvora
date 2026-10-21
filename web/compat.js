/* ES5 guard: run before downloading the Python/WebAssembly loader. */
(function () {
    var query = window.location.search;
    if (/[?&]engine=full(?:&|$)/.test(query)) { return; }
    var ua = navigator.userAgent || '';
    var android = /Android\s+(\d+)/i.exec(ua);
    var chrome = /(?:Chrome|Chromium)\/(\d+)/i.exec(ua);
    var oldAndroid = android && parseInt(android[1], 10) <= 6;
    var oldBrowser = chrome && parseInt(chrome[1], 10) < 90;
    var missingRuntime = typeof window.WebAssembly === 'undefined' || typeof window.Promise === 'undefined';
    if (oldAndroid || oldBrowser || missingRuntime || /[?&]engine=legacy(?:&|$)/.test(query)) {
        var two = /[?&]players=2(?:&|$)/.test(query);
        window.location.replace('legacy/index.html?board=1&v=restored-menu' + (two ? '&players=2' : ''));
    }
}());

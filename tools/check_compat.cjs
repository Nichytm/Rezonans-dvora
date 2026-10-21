/* Routing tests use Node's built-in modules; the browser guard itself is ES5. */
var fs=require('fs'),vm=require('vm'),assert=require('assert');
var code=fs.readFileSync(require('path').join(__dirname,'../web/compat.js'),'utf8');
function run(ua,query,wasm){var redirected=null;var win={Promise:function(){},WebAssembly:wasm?{}:undefined,location:{search:query||'',replace:function(url){redirected=url;}}};vm.runInNewContext(code,{window:win,navigator:{userAgent:ua}});return redirected;}
assert.strictEqual(run('Android 6.0 Chrome/106.0','','yes'),'legacy/index.html?board=1');
assert.strictEqual(run('Android 6.0 Chrome/49.0','?players=2',true),'legacy/index.html?board=1&players=2');
assert.strictEqual(run('Android 14 Chrome/151.0','',true),null);
assert.strictEqual(run('Windows Chrome/49.0','',true),'legacy/index.html?board=1');
assert.strictEqual(run('Windows Chrome/151.0','',false),'legacy/index.html?board=1');
assert.strictEqual(run('Android 6.0 Chrome/49.0','?engine=full',false),null);
assert.strictEqual(run('Windows Chrome/151.0','?engine=legacy',true),'legacy/index.html?board=1');
console.log('PASS: Android 6, old Chrome, missing WASM, modern browsers, explicit engines and two-player routing.');

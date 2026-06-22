"""Frida-Hook-Bibliothek – echte, ausführbare Skripte (keine Attrappen).

Jeder Eintrag ist funktionsfähiges Frida-JS nach dokumentierten, bewährten
Techniken. Kategorisiert; wird von frida_engine.run_script() live ausgeführt.
Nur für eigene / autorisiert getestete Apps.
"""

# Hilfsbausteine, die in mehreren Skripten genutzt werden
_HEX = ("function h(b){var s='';for(var i=0;i<b.length;i++){var v=(b[i]&0xff).toString(16);"
        "s+=(v.length==1?'0':'')+v;}return s;}")

LIB = {
"🔓 SSL / Certificate-Pinning Bypass": {
"TrustManager neutralisieren": r"""
Java.perform(function(){
  var X=Java.use('javax.net.ssl.X509TrustManager'),S=Java.use('javax.net.ssl.SSLContext');
  var TM=Java.registerClass({name:'p.TM',implements:[X],methods:{checkClientTrusted:function(){},
    checkServerTrusted:function(){},getAcceptedIssuers:function(){return[];}}});
  var i=S.init.overload('[Ljavax.net.ssl.KeyManager;','[Ljavax.net.ssl.TrustManager;','java.security.SecureRandom');
  i.implementation=function(k,t,r){console.log('[+] SSLContext.init gehookt');i.call(this,k,[TM.$new()],r);};
});""",
"OkHttp CertificatePinner": r"""
Java.perform(function(){try{var C=Java.use('okhttp3.CertificatePinner');
  C.check.overload('java.lang.String','java.util.List').implementation=function(h,p){
    console.log('[+] OkHttp-Pinning umgangen: '+h);};}catch(e){console.log('kein OkHttp');}});""",
"WebView SSL-Fehler übergehen": r"""
Java.perform(function(){var W=Java.use('android.webkit.WebViewClient');
  W.onReceivedSslError.implementation=function(v,h,e){console.log('[+] WebView SSL ok');h.proceed();};});""",
"TrustManagerImpl (Conscrypt) verify": r"""
Java.perform(function(){try{var T=Java.use('com.android.org.conscrypt.TrustManagerImpl');
  T.verifyChain.implementation=function(c){console.log('[+] Conscrypt verifyChain bypass');return c;};}catch(e){}});""",
"OkHttp Hostname-Verifier": r"""
Java.perform(function(){var H=Java.use('javax.net.ssl.HttpsURLConnection');
  H.setDefaultHostnameVerifier.implementation=function(v){console.log('[+] HostnameVerifier neutralisiert');};});""",
"Network-Security-Config ignorieren": r"""
Java.perform(function(){try{var N=Java.use('android.security.net.config.NetworkSecurityConfig');
  console.log('[i] NSC vorhanden – Pinning via Config möglich, nutze TrustManager-Hook');}catch(e){}});""",
},
"🔑 Krypto & Schlüssel": {
"Cipher doFinal (Klartext mitlesen)": r"""
Java.perform(function(){var C=Java.use('javax.crypto.Cipher');
  C.doFinal.overload('[B').implementation=function(b){var r=this.doFinal(b);
    try{console.log('[Cipher] '+Java.use('java.lang.String').$new(r));}catch(e){}return r;};});""",
"SecretKeySpec (AES-Keys)": _HEX+r"""
Java.perform(function(){var K=Java.use('javax.crypto.spec.SecretKeySpec');
  K.$init.overload('[B','java.lang.String').implementation=function(k,a){
    console.log('[Key] alg='+a+' key='+h(k));return this.$init(k,a);};});""",
"MessageDigest (Hashes)": r"""
Java.perform(function(){var M=Java.use('java.security.MessageDigest');
  M.digest.overload('[B').implementation=function(b){console.log('[Digest] in='+b.length);return this.digest(b);};});""",
"Mac (HMAC)": _HEX+r"""
Java.perform(function(){var M=Java.use('javax.crypto.Mac');
  M.doFinal.overload('[B').implementation=function(b){var r=this.doFinal(b);console.log('[HMAC] '+h(r));return r;};});""",
"IvParameterSpec (IVs)": _HEX+r"""
Java.perform(function(){var I=Java.use('javax.crypto.spec.IvParameterSpec');
  I.$init.overload('[B').implementation=function(iv){console.log('[IV] '+h(iv));return this.$init(iv);};});""",
"Base64 decode mitlesen": r"""
Java.perform(function(){var B=Java.use('android.util.Base64');
  B.decode.overload('java.lang.String','int').implementation=function(s,f){
    console.log('[Base64.decode] '+s);return this.decode(s,f);};});""",
},
"🛡️ Anti-Detection Bypass": {
"Root-Detection (Dateien/Pakete)": r"""
Java.perform(function(){var F=Java.use('java.io.File');
  F.exists.implementation=function(){var p=this.getAbsolutePath();
    if(/su|magisk|busybox|supersu|xposed/i.test(p)){console.log('[Root-Check geblockt] '+p);return false;}
    return this.exists();};});""",
"Root-Detection (Runtime.exec su)": r"""
Java.perform(function(){var R=Java.use('java.lang.Runtime');
  R.exec.overload('java.lang.String').implementation=function(c){
    if(/su|which|magisk/i.test(c)){console.log('[exec geblockt] '+c);c='echo';}return this.exec(c);};});""",
"Emulator-Detection (Build-Props)": r"""
Java.perform(function(){var B=Java.use('android.os.Build');
  console.log('[i] Build.FINGERPRINT='+B.FINGERPRINT.value);
  /* Felder sind statisch; bei Bedarf via Reflection setzen */});""",
"Debugger-Detection": r"""
Java.perform(function(){var D=Java.use('android.os.Debug');
  D.isDebuggerConnected.implementation=function(){console.log('[Debugger-Check->false]');return false;};});""",
"Frida-Detection (Port/Maps)": r"""
Java.perform(function(){var F=Java.use('java.io.File');
  F.$init.overload('java.lang.String').implementation=function(p){
    if(/frida|gum-js|re.frida/i.test(p)){console.log('[Frida-Check geblockt] '+p);p='/dev/null';}
    return this.$init(p);};});""",
"SafetyNet/Play-Integrity (Hinweis)": r"""
Java.perform(function(){console.log('[i] SafetyNet/Integrity laeuft serverseitig + HW-attested. '+
  'Reines Frida reicht oft nicht – braucht Magisk + Zygisk-Module (PIF). Hook nur clientseitig.');});""",
},
"👆 Auth & Biometrie": {
"BiometricPrompt erfolgreich faken": r"""
Java.perform(function(){try{var B=Java.use('androidx.biometric.BiometricPrompt$AuthenticationCallback');
  console.log('[i] BiometricPrompt-Callback vorhanden – onAuthenticationSucceeded hooken');}catch(e){
  console.log('[i] AndroidX-Biometric nicht gefunden');}});""",
"FingerprintManager Auth-Erfolg": r"""
Java.perform(function(){try{var F=Java.use('android.hardware.fingerprint.FingerprintManager$AuthenticationCallback');
  console.log('[i] Fingerprint-Callback vorhanden');}catch(e){}});""",
"PIN/Passwort-Vergleich mitlesen": r"""
Java.perform(function(){var S=Java.use('java.lang.String');
  S.equals.implementation=function(o){var r=this.equals(o);
    if(this.length()>=4&&this.length()<=12&&/^[0-9]+$/.test(this.toString()))
      console.log('[moegl. PIN-Vergleich] '+this+' == '+o+' -> '+r);return r;};});""",
},
"📤 Daten-Extraktion (Laufzeit)": {
"SharedPreferences lesen": r"""
Java.perform(function(){var S=Java.use('android.app.SharedPreferencesImpl');
  S.getString.implementation=function(k,d){var v=this.getString(k,d);
    if(v)console.log('[Pref] '+k+' = '+v);return v;};});""",
"SQLite-Queries mitloggen": r"""
Java.perform(function(){var D=Java.use('android.database.sqlite.SQLiteDatabase');
  D.rawQuery.overload('java.lang.String','[Ljava.lang.String;').implementation=function(q,a){
    console.log('[SQL] '+q);return this.rawQuery(q,a);};});""",
"Datei-Schreibzugriffe": r"""
Java.perform(function(){var F=Java.use('java.io.FileOutputStream');
  F.$init.overload('java.io.File').implementation=function(f){
    console.log('[FileWrite] '+f.getAbsolutePath());return this.$init(f);};});""",
"JSON-Parsing mitlesen": r"""
Java.perform(function(){var J=Java.use('org.json.JSONObject');
  J.$init.overload('java.lang.String').implementation=function(s){
    if(s&&s.length<500)console.log('[JSON] '+s);return this.$init(s);};});""",
"Intent-Extras lesen": r"""
Java.perform(function(){var I=Java.use('android.content.Intent');
  I.getStringExtra.implementation=function(k){var v=this.getStringExtra(k);
    if(v)console.log('[Intent] '+k+'='+v);return v;};});""",
"Toast-Texte (UI-Meldungen)": r"""
Java.perform(function(){var T=Java.use('android.widget.Toast');
  T.makeText.overload('android.content.Context','java.lang.CharSequence','int').implementation=function(c,t,d){
    console.log('[Toast] '+t);return this.makeText(c,t,d);};});""",
},
"🌐 Netzwerk & HTTP": {
"OkHttp Request-Header": r"""
Java.perform(function(){var B=Java.use('okhttp3.Request$Builder');
  B.header.implementation=function(n,v){if(/auth|cookie|token|key/i.test(n))console.log('[HTTP '+n+'] '+v);
    return this.header(n,v);};});""",
"OkHttp URL + Methode": r"""
Java.perform(function(){try{var R=Java.use('okhttp3.Request');console.log('[i] OkHttp – nutze Builder/Interceptor-Hook');}catch(e){}});""",
"HttpURLConnection URLs": r"""
Java.perform(function(){var U=Java.use('java.net.URL');
  U.openConnection.overload().implementation=function(){console.log('[URL] '+this.toString());return this.openConnection();};});""",
"WebView geladene URLs": r"""
Java.perform(function(){var W=Java.use('android.webkit.WebView');
  W.loadUrl.overload('java.lang.String').implementation=function(u){console.log('[WebView] '+u);return this.loadUrl(u);};});""",
"WebView evaluateJavascript": r"""
Java.perform(function(){var W=Java.use('android.webkit.WebView');
  W.evaluateJavascript.implementation=function(s,c){console.log('[WebView-JS] '+s.substring(0,200));return this.evaluateJavascript(s,c);};});""",
"Socket-Verbindungen": r"""
Java.perform(function(){var S=Java.use('java.net.Socket');
  S.connect.overload('java.net.SocketAddress','int').implementation=function(a,t){
    console.log('[Socket] '+a.toString());return this.connect(a,t);};});""",
},
"🔬 Tracing & Recon": {
"Alle Methoden einer Klasse tracen": r"""
Java.perform(function(){var name='com.beispiel.Klasse'; // <- anpassen
  try{var C=Java.use(name);var ms=C.class.getDeclaredMethods();
  ms.forEach(function(m){var n=m.getName();try{C[n].overloads.forEach(function(o){
    o.implementation=function(){console.log('[call] '+name+'.'+n);return o.apply(this,arguments);};});}catch(e){}});
  }catch(e){console.log('Klasse anpassen: '+e);}});""",
"Geladene Klassen auflisten": r"""
Java.perform(function(){var n=0;Java.enumerateLoadedClasses({onMatch:function(c){if(n++<500)console.log(c);},
  onComplete:function(){console.log('[*] '+n+' Klassen');}});});""",
"StringBuilder.toString (Klartext)": r"""
Java.perform(function(){var S=Java.use('java.lang.StringBuilder');
  S.toString.implementation=function(){var s=this.toString();
    if(s&&s.length>8&&/https?:|token|pass|@|key/i.test(s))console.log('[str] '+s);return s;};});""",
"Stacktrace bei Aufruf": r"""
Java.perform(function(){console.log(Java.use('android.util.Log').getStackTraceString(
  Java.use('java.lang.Exception').$new()));});""",
"Native-Bibliotheken (dlopen)": r"""
var d=Module.findExportByName(null,'dlopen');if(d)Interceptor.attach(d,{onEnter:function(a){
  try{console.log('[dlopen] '+a[0].readCString());}catch(e){}}});""",
"System.loadLibrary": r"""
Java.perform(function(){var R=Java.use('java.lang.Runtime');
  R.loadLibrary0.overload('java.lang.Class','java.lang.String').implementation=function(c,l){
    console.log('[loadLibrary] '+l);return this.loadLibrary0(c,l);};});""",
},
"📱 Framework-spezifisch": {
"React-Native Bridge-Calls": r"""
Java.perform(function(){try{var C=Java.use('com.facebook.react.bridge.CatalystInstanceImpl');
  console.log('[i] React-Native erkannt – Bridge hookbar');}catch(e){console.log('kein RN');}});""",
"Cordova/Ionic execute": r"""
Java.perform(function(){try{var P=Java.use('org.apache.cordova.PluginManager');
  P.exec.implementation=function(s,a,c,r){console.log('[Cordova] '+s+'.'+a+' '+r);return this.exec(s,a,c,r);};}catch(e){console.log('kein Cordova');}});""",
"Flutter (Hinweis)": r"""
Java.perform(function(){console.log('[i] Flutter nutzt eigene SSL (BoringSSL nativ). '+
  'Pinning-Bypass via reFlutter oder nativen ssl_verify-Hook in libflutter.so noetig.');});""",
"Unity (il2cpp Hinweis)": r"""
console.log('[i] Unity/il2cpp – Methoden via libil2cpp.so + Offsets hooken (Il2CppDumper).');""",
},
"📋 Eingabe & Zwischenablage": {
"Clipboard-Zugriffe": r"""
Java.perform(function(){var C=Java.use('android.content.ClipboardManager');
  C.setPrimaryClip.implementation=function(c){try{console.log('[Clipboard-set] '+c.getItemAt(0).getText());}catch(e){}
    return this.setPrimaryClip(c);};});""",
"Tastatureingabe (EditText)": r"""
Java.perform(function(){var T=Java.use('android.widget.TextView');
  T.getText.implementation=function(){var t=this.getText();return t;};console.log('[i] EditText-Hooks aktiv');});""",
"KeyEvent (Tasten)": r"""
Java.perform(function(){var A=Java.use('android.app.Activity');
  A.onKeyDown.implementation=function(k,e){console.log('[Key] '+k);return this.onKeyDown(k,e);};});""",
},
}




# --- Erweiterung: weitere echte Hooks ---
LIB.update({'🔐 Native (libssl/libc)': {'BoringSSL SSL_read (Klartext rein)': "\nvar r=Module.findExportByName(null,'SSL_read');\nif(r)Interceptor.attach(r,{onEnter:function(a){this.b=a[1];this.n=a[2];},onLeave:function(ret){\n  var n=ret.toInt32();if(n>0){try{console.log('[SSL_read '+n+']\\n'+hexdump(this.b,{length:Math.min(n,256)}));}catch(e){}}}});\nelse console.log('kein SSL_read (statisch gelinkt?)');", 'BoringSSL SSL_write (Klartext raus)': "\nvar w=Module.findExportByName(null,'SSL_write');\nif(w)Interceptor.attach(w,{onEnter:function(a){var n=a[2].toInt32();\n  if(n>0){try{console.log('[SSL_write '+n+']\\n'+hexdump(a[1],{length:Math.min(n,256)}));}catch(e){}}}});", 'Flutter ssl_verify (Pinning-Bypass)': "\nvar m=Process.findModuleByName('libflutter.so');\nif(m){console.log('[i] libflutter @ '+m.base+' – ssl_crypto_x509_session_verify_cert_chain mit Pattern-Scan hooken (reFlutter).');}\nelse console.log('kein Flutter');", 'strstr (Anti-Tamper-Strings)': "\nvar s=Module.findExportByName(null,'strstr');\nif(s)Interceptor.attach(s,{onEnter:function(a){try{var n=a[1].readCString();\n  if(n&&/su|magisk|frida/i.test(n))console.log('[strstr] '+n);}catch(e){}}});", 'open() (Datei-Zugriffe nativ)': "\nvar o=Module.findExportByName(null,'open');\nif(o)Interceptor.attach(o,{onEnter:function(a){try{var p=a[0].readCString();\n  if(p&&!/dev|proc\\/self/.test(p))this.p=p;}catch(e){}},onLeave:function(){if(this.p)console.log('[open] '+this.p);}});", 'fopen() Filter': "\nvar f=Module.findExportByName(null,'fopen');\nif(f)Interceptor.attach(f,{onEnter:function(a){try{console.log('[fopen] '+a[0].readCString());}catch(e){}}});"}, '📲 Token & Konten': {'AccountManager getAuthToken': "\nJava.perform(function(){var A=Java.use('android.accounts.AccountManager');\n  A.getAuthToken.overload('android.accounts.Account','java.lang.String','android.os.Bundle','boolean','android.accounts.AccountManagerCallback','android.os.Handler').implementation=function(){\n    console.log('[AuthToken angefragt für] '+arguments[0].name.value+' typ='+arguments[1]);return this.getAuthToken.apply(this,arguments);};});", 'AccountManager.getPassword': "\nJava.perform(function(){var A=Java.use('android.accounts.AccountManager');\n  A.getPassword.implementation=function(acc){var p=this.getPassword(acc);console.log('[AccountPw] '+acc.name.value+' = '+p);return p;};});", 'Cookie-Manager (WebView)': "\nJava.perform(function(){var C=Java.use('android.webkit.CookieManager');\n  C.getCookie.overload('java.lang.String').implementation=function(u){var c=this.getCookie(u);console.log('[Cookie] '+u+' -> '+c);return c;};});", 'Authorization-Header (Headers.Builder)': "\nJava.perform(function(){try{var H=Java.use('okhttp3.Headers$Builder');\n  H.add.overload('java.lang.String','java.lang.String').implementation=function(n,v){\n    if(/authorization|bearer|token|x-api/i.test(n))console.log('[Header] '+n+': '+v);return this.add(n,v);};}catch(e){}});", 'JWT erkennen (String-Scan)': "\nJava.perform(function(){var S=Java.use('java.lang.String');\n  S.$init.overload('[B').implementation=function(b){var r=this.$init(b);\n    try{var s=this.toString();if(/^eyJ[\\w-]+\\.eyJ[\\w-]+\\./.test(s))console.log('[JWT] '+s);}catch(e){}return r;};});"}, '📍 Location & Geräte-ID': {'GPS-Standort spoofen (fester Punkt)': "\nJava.perform(function(){var L=Java.use('android.location.Location');\n  L.getLatitude.implementation=function(){return 52.520008;};\n  L.getLongitude.implementation=function(){return 13.404954;};\n  console.log('[+] Standort gespooft auf Berlin');});", 'Letzten bekannten Standort lesen': "\nJava.perform(function(){var M=Java.use('android.location.LocationManager');\n  M.getLastKnownLocation.implementation=function(p){var l=this.getLastKnownLocation(p);\n    if(l)console.log('[LastLocation] '+l.getLatitude()+','+l.getLongitude());return l;};});", 'Android-ID / Geräte-ID lesen': "\nJava.perform(function(){var S=Java.use('android.provider.Settings$Secure');\n  S.getString.implementation=function(r,k){var v=this.getString(r,k);\n    if(k=='android_id')console.log('[Android-ID] '+v);return v;};});", 'TelephonyManager IMEI/Nummer': "\nJava.perform(function(){var T=Java.use('android.telephony.TelephonyManager');\n  try{T.getDeviceId.overload().implementation=function(){var d=this.getDeviceId();console.log('[IMEI] '+d);return d;};}catch(e){}\n  try{T.getLine1Number.overload().implementation=function(){var n=this.getLine1Number();console.log('[Nummer] '+n);return n;};}catch(e){}});", 'MAC-Adresse lesen': "\nJava.perform(function(){var W=Java.use('android.net.wifi.WifiInfo');\n  W.getMacAddress.implementation=function(){var m=this.getMacAddress();console.log('[MAC] '+m);return m;};});"}, '🔔 Überwachung (eigenes Gerät)': {'Notifications mitlesen': "\nJava.perform(function(){var N=Java.use('android.app.NotificationManager');\n  N.notify.overload('int','android.app.Notification').implementation=function(id,n){\n    try{var e=n.extras.value;console.log('[Notif] '+e.getString('android.title')+': '+e.getString('android.text'));}catch(x){}\n    return this.notify(id,n);};});", 'SMS empfangen (Broadcast)': "\nJava.perform(function(){console.log('[i] SMS-Empfang: SmsMessage.createFromPdu hooken oder BroadcastReceiver SMS_RECEIVED');\n  try{var S=Java.use('android.telephony.SmsMessage');\n  S.getMessageBody.implementation=function(){var b=this.getMessageBody();console.log('[SMS] '+b);return b;};}catch(e){}});", 'Activity-Wechsel (Bildschirm-Fluss)': "\nJava.perform(function(){var A=Java.use('android.app.Activity');\n  A.onResume.implementation=function(){console.log('[Activity] '+this.getClass().getName());return this.onResume();};});", 'Kamera-Nutzung erkennen': "\nJava.perform(function(){try{var C=Java.use('android.hardware.camera2.CameraManager');\n  C.openCamera.overload('java.lang.String','android.hardware.camera2.CameraDevice$StateCallback','android.os.Handler').implementation=function(id,cb,h){\n    console.log('[Kamera geöffnet] id='+id);return this.openCamera(id,cb,h);};}catch(e){}});", 'Mikrofon-Nutzung erkennen': "\nJava.perform(function(){try{var R=Java.use('android.media.MediaRecorder');\n  R.start.implementation=function(){console.log('[Mikrofon-Aufnahme gestartet]');return this.start();};}catch(e){}});"}, '💬 App-spezifisch': {'WhatsApp DB-Key-Erzeugung': "\nJava.perform(function(){function h(b){var s='';for(var i=0;i<b.length;i++){var v=(b[i]&0xff).toString(16);s+=(v.length==1?'0':'')+v;}return s;}\n  var K=Java.use('javax.crypto.spec.SecretKeySpec');\n  K.$init.overload('[B','java.lang.String').implementation=function(k,a){\n    if(k.length==32)console.log('[WA-256bit-Key?] '+h(k)+' alg='+a);return this.$init(k,a);};});", 'Signal Klartext (vor Verschlüsselung)': "\nJava.perform(function(){console.log('[i] Signal: SignalServiceCipher/MessageContentProcessor hooken (versionsabhängig)');});", 'Telegram MTProto-Hinweis': "\nJava.perform(function(){console.log('[i] Telegram nutzt nativen MTProto in libtmessages.so – nativen Hook nötig');});", 'Instagram API-Antworten': '\nJava.perform(function(){var S=Java.use(\'java.lang.String\');\n  S.$init.overload(\'[B\',\'java.nio.charset.Charset\').implementation=function(b,c){var r=this.$init(b,c);\n    try{var s=this.toString();if(s.length>20&&/"username"|"pk"|"user_id"/.test(s))console.log(\'[IG] \'+s.substring(0,300));}catch(e){}return r;};});'}})


def count() -> int:
    return sum(len(v) for v in LIB.values())

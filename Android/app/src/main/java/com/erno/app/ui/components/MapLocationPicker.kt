package com.erno.app.ui.components

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.LocationManager
import android.location.Location
import android.location.LocationListener
import android.os.Build
import android.os.CancellationSignal
import android.os.Handler
import android.os.Looper
import java.util.concurrent.atomic.AtomicBoolean
import android.webkit.JavascriptInterface
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import org.json.JSONObject

@Composable
fun MapLocationPicker(address: String, onSelection: (String, Double, Double) -> Unit, modifier: Modifier = Modifier) {
    val context = LocalContext.current
    var query by remember { mutableStateOf("") }; var results by remember { mutableStateOf(listOf<JSONObject>()) }
    var webView by remember { mutableStateOf<WebView?>(null) }; var error by remember { mutableStateOf<String?>(null) }
    val permission = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { grants ->
        if (grants.values.any { it }) locate(context, webView) else error = "Location permission was denied. Search or enter the address manually."
    }
    Column(modifier) {
        OutlinedTextField(query, { query=it; webView?.evaluateJavascript("window.ErrnoMapAPI&&ErrnoMapAPI.search(${JSONObject.quote(it)})", null) }, label={Text("Search address")}, modifier=Modifier.fillMaxWidth(), singleLine=true)
        if (error != null) Text(error!!, color=MaterialTheme.colorScheme.error, style=MaterialTheme.typography.bodySmall)
        if (results.isNotEmpty()) LazyColumn(Modifier.heightIn(max=160.dp)) { items(results) { item -> Text(item.optString("label"), Modifier.fillMaxWidth().clickable { val label=item.optString("label"); val lat=item.optDouble("latitude"); val lng=item.optDouble("longitude"); onSelection(label,lat,lng); webView?.evaluateJavascript("ErrnoMapAPI.select({latitude:$lat,longitude:$lng,label:${JSONObject.quote(label)}})",null); results=emptyList() }.padding(12.dp)) } }
        AndroidView(factory={ ctx -> WebView(ctx).apply {
            settings.javaScriptEnabled=true; settings.domStorageEnabled=true; settings.allowFileAccess=true; settings.allowContentAccess=true
            webViewClient=WebViewClient(); addJavascriptInterface(object { @JavascriptInterface fun onMapEvent(json:String) { post { try { val obj=JSONObject(json); when(obj.optString("type")){"selection"->onSelection(obj.optString("address",address),obj.getDouble("latitude"),obj.getDouble("longitude"));"results"->{val arr=obj.optJSONArray("items");results=(0 until (arr?.length()?:0)).map{arr!!.getJSONObject(it)};error=obj.optString("error").takeIf{it.isNotBlank()} } ;"error"->error="Map tiles could not be loaded. Enter the address manually."} } catch (_:Exception){} } } }, "ErrnoMap")
            loadUrl("file:///android_asset/errno-map/index.html?photon=${android.net.Uri.encode(com.erno.app.BuildConfig.ERRNO_PHOTON_ENDPOINT)}&osrm=${android.net.Uri.encode(com.erno.app.BuildConfig.ERRNO_OSRM_ENDPOINT)}&style=${android.net.Uri.encode(com.erno.app.BuildConfig.ERRNO_MAP_STYLE_URL)}")
        } }, update={ webView=it }, modifier=Modifier.fillMaxWidth().height(260.dp))
        TextButton(onClick={ if (ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION)==PackageManager.PERMISSION_GRANTED || ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION)==PackageManager.PERMISSION_GRANTED) locate(context,webView) else permission.launch(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION,Manifest.permission.ACCESS_COARSE_LOCATION)) }) { Text("Use my current location") }
    }
}
private fun locate(context: Context, view: WebView?) {
    val manager=context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
    val provider=when { manager.isProviderEnabled(LocationManager.GPS_PROVIDER)->LocationManager.GPS_PROVIDER; manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)->LocationManager.NETWORK_PROVIDER; else->null }
    if(provider==null){ view?.evaluateJavascript("document.getElementById('status').textContent='Location services are off. Select a pin or enter address manually.'",null); return }
    fun accepted(location:Location?) { if(location!=null && System.currentTimeMillis()-location.time<120_000) view?.evaluateJavascript("ErrnoMapAPI.setLocation(${location.latitude},${location.longitude},'Current location',true)",null) else view?.evaluateJavascript("document.getElementById('status').textContent='Could not get a fresh GPS fix. Select a pin or enter address manually.'",null) }
    try {
        if(Build.VERSION.SDK_INT>=30) manager.getCurrentLocation(provider,CancellationSignal(),context.mainExecutor,::accepted)
        else {
            val done=AtomicBoolean(false); lateinit var listener:LocationListener
            listener=object:LocationListener {
                override fun onLocationChanged(location:Location){ if(done.compareAndSet(false,true)){manager.removeUpdates(this);accepted(location)} }
                @Deprecated("Deprecated in Android") override fun onStatusChanged(provider:String?,status:Int,extras:android.os.Bundle?) {}
                override fun onProviderEnabled(provider:String) {}
                override fun onProviderDisabled(provider:String) {}
            }
            manager.requestLocationUpdates(provider,0L,0f,listener,Looper.getMainLooper())
            Handler(Looper.getMainLooper()).postDelayed({ if(done.compareAndSet(false,true)){manager.removeUpdates(listener);accepted(null)} },12_000)
        }
    } catch(_:SecurityException){ view?.evaluateJavascript("document.getElementById('status').textContent='Location permission was denied. Select a pin or enter address manually.'",null) }
}

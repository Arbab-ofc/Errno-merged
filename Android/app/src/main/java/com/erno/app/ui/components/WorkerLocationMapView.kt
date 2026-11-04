package com.erno.app.ui.components

import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.erno.app.BuildConfig
import com.erno.app.data.model.ApproximateRoute
import com.erno.app.data.model.MapCoordinate
import com.erno.app.data.model.NearbyWorker
import org.json.JSONArray
import org.json.JSONObject

@Composable
fun WorkerLocationMapView(
    locationName: String,
    distanceText: String = "Job location",
    latitude: Double? = null,
    longitude: Double? = null,
    isDarkTheme: Boolean = true,
    nearbyWorkers: List<NearbyWorker> = emptyList(),
    workerLocation: MapCoordinate? = null,
    route: ApproximateRoute? = null
) {
    val renderState=rememberUpdatedState(MapRenderState(nearbyWorkers,workerLocation,route))
    Surface(modifier=Modifier.fillMaxWidth().height(220.dp).clip(RoundedCornerShape(16.dp))) {
        AndroidView(factory={ context -> WebView(context).apply {
            settings.javaScriptEnabled=true; settings.domStorageEnabled=true; settings.allowFileAccess=true
            webViewClient=object:WebViewClient(){ override fun onPageFinished(view:WebView,url:String){tag="errno-map-ready"; view.evaluateJavascript(renderJs(renderState.value),null) } }
            val point=if(latitude!=null && longitude!=null) "&lat=$latitude&lng=$longitude" else ""
            loadUrl("file:///android_asset/errno-map/index.html?photon=${android.net.Uri.encode(BuildConfig.ERRNO_PHOTON_ENDPOINT)}&osrm=${android.net.Uri.encode(BuildConfig.ERRNO_OSRM_ENDPOINT)}&tiles=${android.net.Uri.encode(BuildConfig.ERRNO_TILE_ENDPOINT)}&style=${android.net.Uri.encode(BuildConfig.ERRNO_MAP_STYLE_URL)}$point")
        } }, update={ view -> if(view.tag=="errno-map-ready") view.evaluateJavascript(renderJs(renderState.value),null) }, modifier=Modifier.fillMaxWidth().height(220.dp))
    }
}
private data class MapRenderState(val workers:List<NearbyWorker>,val worker:MapCoordinate?,val route:ApproximateRoute?)
private fun renderJs(s:MapRenderState):String {
    val workers=JSONArray().apply { s.workers.forEach { put(JSONObject().put("latitude",it.latitude).put("longitude",it.longitude).put("distance_km",it.distanceKm)) } }
    val prefix="window.ErrnoMapAPI&&ErrnoMapAPI.setWorkers($workers);"
    val worker=s.worker?.let { "ErrnoMapAPI.setWorker(${it.latitude},${it.longitude});" } ?: ""
    val route=s.route?.let { r ->
        val points=JSONArray().apply { r.coordinates.forEach { put(JSONArray().put(it.latitude).put(it.longitude)) } }
        "ErrnoMapAPI.setRoute($points,${r.distanceKm},${r.durationMinutes});"
    } ?: ""
    return prefix+worker+route
}

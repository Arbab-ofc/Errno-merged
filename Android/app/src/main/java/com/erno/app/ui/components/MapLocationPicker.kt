package com.erno.app.ui.components

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.ui.Alignment
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.erno.app.BuildConfig
import com.google.android.gms.maps.CameraUpdateFactory
import com.google.android.gms.maps.model.CameraPosition
import com.google.android.gms.maps.model.LatLng
import com.google.maps.android.compose.GoogleMap
import com.google.maps.android.compose.MapProperties
import com.google.maps.android.compose.MapUiSettings
import com.google.maps.android.compose.Marker
import com.google.maps.android.compose.MarkerState
import com.google.maps.android.compose.rememberCameraPositionState
import com.google.maps.android.compose.rememberUpdatedMarkerState
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.Job
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.net.URLEncoder
import java.util.Locale

private data class PhotonResult(val label: String, val latitude: Double, val longitude: Double)
private val photonClient = OkHttpClient()

@Composable
fun MapLocationPicker(
    address: String,
    latitude: Double? = null,
    longitude: Double? = null,
    onSelection: (String, Double, Double) -> Unit,
    modifier: Modifier = Modifier
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var query by remember { mutableStateOf("") }
    var results by remember { mutableStateOf(emptyList<PhotonResult>()) }
    var error by remember { mutableStateOf<String?>(null) }
    var mapLoaded by remember { mutableStateOf(false) }
    var mapError by remember { mutableStateOf<String?>(null) }
    var reverseError by remember { mutableStateOf<String?>(null) }
    var selected by remember { mutableStateOf(if (isCoordinate(latitude, longitude)) LatLng(latitude!!, longitude!!) else null) }
    var selectionRevision by remember { mutableIntStateOf(0) }
    var reverseJob by remember { mutableStateOf<Job?>(null) }
    val latestAddress by rememberUpdatedState(address)
    val latestLatitude by rememberUpdatedState(latitude)
    val latestLongitude by rememberUpdatedState(longitude)
    val latestOnSelection by rememberUpdatedState(onSelection)
    fun choosePoint(point: LatLng) {
        selected = point
        reverseError = null
        val revision = ++selectionRevision
        reverseJob?.cancel()
        latestOnSelection(latestAddress, point.latitude, point.longitude)
        reverseJob = scope.launch {
            kotlinx.coroutines.delay(500)
            try {
                val label = reversePhoton(point.latitude, point.longitude)
                if (revision == selectionRevision && latestLatitude == point.latitude && latestLongitude == point.longitude) {
                    if (label.isNotBlank()) latestOnSelection(label, point.latitude, point.longitude)
                }
            } catch (_: Exception) {
                if (revision == selectionRevision && latestLatitude == point.latitude && latestLongitude == point.longitude) {
                    reverseError = "Address lookup is unavailable. Edit the address above if needed."
                }
            }
        }
    }
    val initial = selected ?: LatLng(28.6139, 77.2090)
    val camera = rememberCameraPositionState { position = CameraPosition.fromLatLngZoom(initial, if (selected == null) 10f else 16f) }
    val pinMarkerState = selected?.let { rememberUpdatedMarkerState(it) }
    LaunchedEffect(pinMarkerState?.position, pinMarkerState?.isDragging) {
        val markerPoint = pinMarkerState?.position
        if (markerPoint != null && pinMarkerState.isDragging.not() && selected != markerPoint) {
            choosePoint(markerPoint)
        }
    }
    val locationPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { grants ->
        if (grants.values.any { it } || hasMapLocationPermission(context)) {
            val manager = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
            val enabled = manager.isProviderEnabled(LocationManager.GPS_PROVIDER) || manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)
            val location = if (enabled && hasMapLocationPermission(context)) lastLocation(manager) else null
            if (!enabled) error = "Location services are off. You can still select the pin or enter the address."
            else if (location == null) error = "No recent GPS fix. Tap the map to place the pin or enter the address."
            else {
                val point = LatLng(location.latitude, location.longitude)
                error = null
                choosePoint(point)
                scope.launch { camera.animate(CameraUpdateFactory.newLatLngZoom(point, 16f)) }
            }
        } else error = "Location permission was denied. You can still select the pin or enter the address."
    }
    LaunchedEffect(latitude, longitude) {
        if (isCoordinate(latitude, longitude)) {
            val point = LatLng(latitude!!, longitude!!)
            if (selected != point) { selected = point; camera.position = CameraPosition.fromLatLngZoom(point, 16f) }
        } else if (latitude == null && longitude == null && selected != null) {
            selected = null
            selectionRevision++
            reverseJob?.cancel()
        }
    }
    LaunchedEffect(Unit) {
        kotlinx.coroutines.delay(15_000)
        if (!mapLoaded) mapError = "Map is taking longer to load. Check your connection or API key; you can still enter the address."
    }
    Column(modifier, verticalArrangement = Arrangement.spacedBy(8.dp)) {
        OutlinedTextField(query, { query = it; error = null }, label = { Text("Search address") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
        LaunchedEffect(query) {
            val search = query.trim()
            if (search.length >= 3) {
                kotlinx.coroutines.delay(350)
                try { results = searchPhoton(search) } catch (_: Exception) { results = emptyList(); error = "Address search is unavailable. You can place the pin manually." }
            } else results = emptyList()
        }
        if (results.isNotEmpty()) LazyColumn(Modifier.heightIn(max = 150.dp)) {
            items(results) { item -> Text(item.label, Modifier.fillMaxWidth().clickable {
                val point = LatLng(item.latitude, item.longitude)
                selected = point; reverseJob?.cancel(); selectionRevision++
                onSelection(item.label, item.latitude, item.longitude); results = emptyList(); query = item.label; reverseError = null
                scope.launch { camera.animate(CameraUpdateFactory.newLatLngZoom(point, 16f)) }
            }.padding(12.dp)) }
        }
        Box(Modifier.fillMaxWidth().height(260.dp)) {
            GoogleMap(
                modifier = Modifier.fillMaxSize(),
                cameraPositionState = camera,
                properties = MapProperties(isMyLocationEnabled = hasMapLocationPermission(context)),
                uiSettings = MapUiSettings(myLocationButtonEnabled = false, mapToolbarEnabled = false),
                onMapLoaded = { mapLoaded = true; mapError = null },
                onMapClick = { point -> choosePoint(point); error = null }
            ) {
                pinMarkerState?.let { Marker(state = it, title = "Shop location", draggable = true) }
            }
            if (!mapLoaded) Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            TextButton(onClick = { if (hasMapLocationPermission(context)) locationPermission.launch(emptyArray()) else locationPermission.launch(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)) }) { Text("Use current location") }
            TextButton(onClick = { selected?.let { scope.launch { camera.animate(CameraUpdateFactory.newLatLngZoom(it, 16f)) } } }, enabled = selected != null) { Text("Recenter pin") }
        }
        selected?.let { Text(String.format(Locale.US, "Selected: %.6f, %.6f", it.latitude, it.longitude), style = MaterialTheme.typography.bodySmall) }
        mapError?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
        error?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
        reverseError?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
    }
}

private fun isCoordinate(lat: Double?, lng: Double?) = lat != null && lng != null && lat.isFinite() && lng.isFinite() && lat in -90.0..90.0 && lng in -180.0..180.0
private fun hasMapLocationPermission(context: Context) = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED || ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
private fun lastLocation(manager: LocationManager): Location? = try { listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER).mapNotNull { manager.getLastKnownLocation(it) }.maxByOrNull { it.time }?.takeIf { System.currentTimeMillis() - it.time < 120_000 } } catch (_: SecurityException) { null }

private suspend fun searchPhoton(query: String): List<PhotonResult> = withContext(Dispatchers.IO) {
    val encoded = URLEncoder.encode(query, Charsets.UTF_8.name())
    val request = Request.Builder().url("${BuildConfig.ERRNO_PHOTON_ENDPOINT.trimEnd('/')}/api/?q=$encoded&limit=6&lang=en").build()
    photonClient.newCall(request).execute().use { response ->
        check(response.isSuccessful) { "Photon returned ${response.code}" }
        val features = JSONObject(response.body?.string().orEmpty()).optJSONArray("features") ?: return@withContext emptyList()
        (0 until features.length()).mapNotNull { index ->
            val feature = features.getJSONObject(index); val coords = feature.optJSONObject("geometry")?.optJSONArray("coordinates") ?: return@mapNotNull null
            if (coords.length() < 2) return@mapNotNull null
            val props = feature.optJSONObject("properties") ?: JSONObject()
            val label = listOf("name", "street", "housenumber", "district", "city", "state", "country").mapNotNull { props.optString(it).takeIf(String::isNotBlank) }.distinct().joinToString(", ")
            if (label.isBlank()) return@mapNotNull null
            PhotonResult(label, coords.getDouble(1), coords.getDouble(0))
        }
    }
}

private suspend fun reversePhoton(latitude: Double, longitude: Double): String = withContext(Dispatchers.IO) {
    val request = Request.Builder()
        .url("${BuildConfig.ERRNO_PHOTON_ENDPOINT.trimEnd('/')}/reverse?lat=$latitude&lon=$longitude")
        .build()
    photonClient.newCall(request).execute().use { response ->
        check(response.isSuccessful) { "Photon returned ${response.code}" }
        val feature = JSONObject(response.body?.string().orEmpty()).optJSONArray("features")?.optJSONObject(0)
            ?: return@withContext ""
        val props = feature.optJSONObject("properties") ?: JSONObject()
        listOf("name", "housenumber", "street", "district", "locality", "city", "state", "postcode", "country")
            .mapNotNull { props.optString(it).takeIf(String::isNotBlank) }.distinct().joinToString(", ")
    }
}

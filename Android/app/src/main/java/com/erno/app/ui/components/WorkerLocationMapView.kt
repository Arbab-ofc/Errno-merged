package com.erno.app.ui.components

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.LocationManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.ui.Alignment
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import kotlinx.coroutines.launch
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.draw.clip
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.erno.app.data.model.MapCoordinate
import com.erno.app.data.model.NearbyWorker
import com.google.android.gms.maps.model.CameraPosition
import com.google.android.gms.maps.model.LatLng
import com.google.maps.android.compose.GoogleMap
import com.google.maps.android.compose.MapProperties
import com.google.maps.android.compose.MapUiSettings
import com.google.maps.android.compose.Marker
import com.google.maps.android.compose.MarkerState
import com.google.maps.android.compose.rememberCameraPositionState

@Composable
fun WorkerLocationMapView(
    locationName: String,
    distanceText: String = "Shop location",
    latitude: Double? = null,
    longitude: Double? = null,
    isDarkTheme: Boolean = true,
    nearbyWorkers: List<NearbyWorker> = emptyList(),
    workerLocation: MapCoordinate? = null
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var permissionGranted by remember { mutableStateOf(hasLocationPermission(context)) }
    var message by remember { mutableStateOf<String?>(null) }
    var mapLoaded by remember { mutableStateOf(false) }
    var mapError by remember { mutableStateOf<String?>(null) }
    val permission = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { grants ->
        permissionGranted = grants.values.any { it } || hasLocationPermission(context)
        if (!permissionGranted) message = "Location permission denied. Your location is not shown."
        else {
            val manager = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
            if (!manager.isProviderEnabled(LocationManager.GPS_PROVIDER) && !manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) message = "Location services are off. The shop address remains available."
        }
    }
    val shop = if (latitude != null && longitude != null && latitude.isFinite() && longitude.isFinite() && latitude in -90.0..90.0 && longitude in -180.0..180.0) LatLng(latitude, longitude) else null
    val initial = shop ?: LatLng(0.0, 0.0)
    val camera = rememberCameraPositionState { position = CameraPosition.fromLatLngZoom(initial, if (shop == null) 5f else 15f) }
    LaunchedEffect(shop) { kotlinx.coroutines.delay(15_000); if (shop != null && !mapLoaded) mapError = "Map is unavailable. Use the shop address below." }
    Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp))) {
        Box(Modifier.fillMaxWidth().height(220.dp)) {
            if (shop == null) {
                Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("Shop coordinates are unavailable. Use the saved address.", style = MaterialTheme.typography.bodySmall)
                }
            } else {
                GoogleMap(
                    modifier = Modifier.fillMaxSize(), cameraPositionState = camera,
                    properties = MapProperties(isMyLocationEnabled = permissionGranted),
                    uiSettings = MapUiSettings(myLocationButtonEnabled = false, mapToolbarEnabled = false),
                    onMapLoaded = { mapLoaded = true; mapError = null }
                ) {
                    Marker(state = MarkerState(shop), title = locationName.ifBlank { "Shop" }, snippet = distanceText)
                    workerLocation?.let { point -> if (point.latitude.isFinite() && point.longitude.isFinite() && point.latitude in -90.0..90.0 && point.longitude in -180.0..180.0) Marker(state = MarkerState(LatLng(point.latitude, point.longitude)), title = "Worker location") }
                    nearbyWorkers.forEach { worker -> if (worker.latitude.isFinite() && worker.longitude.isFinite() && worker.latitude in -90.0..90.0 && worker.longitude in -180.0..180.0) Marker(state = MarkerState(LatLng(worker.latitude, worker.longitude)), title = "Available worker", snippet = "${worker.distanceKm} km away") }
                }
                if (!mapLoaded) Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
            }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            TextButton(onClick = { shop?.let { camera.position = CameraPosition.fromLatLngZoom(it, 16f) } }, enabled = shop != null) { Text("Recenter shop") }
            TextButton(onClick = { if (permissionGranted) {
                val manager = context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
                val enabled = manager.isProviderEnabled(LocationManager.GPS_PROVIDER) || manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER)
                if (!enabled) message = "Location services are off. The shop address remains available."
                else {
                    val point = currentForegroundLocation(manager)
                    if (point == null) message = "No recent GPS fix. Check location services or use the shop address."
                    else { message = "Your location is shown only while permission is granted."; scope.launch { camera.animate(com.google.android.gms.maps.CameraUpdateFactory.newLatLngZoom(LatLng(point.latitude, point.longitude), 16f)) } }
                }
            } else permission.launch(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)) }) { Text("My location") }
        }
        Text(locationName.ifBlank { "Shop coordinates are not available" }, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(horizontal = 12.dp))
        mapError?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(horizontal = 12.dp)) }
        message?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall, modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp)) }
    }
}

private fun hasLocationPermission(context: Context) = ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED || ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED
private fun currentForegroundLocation(manager: LocationManager) = try {
    listOf(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER).mapNotNull { manager.getLastKnownLocation(it) }
        .maxByOrNull { it.time }?.takeIf { System.currentTimeMillis() - it.time < 120_000 }
} catch (_: SecurityException) { null }

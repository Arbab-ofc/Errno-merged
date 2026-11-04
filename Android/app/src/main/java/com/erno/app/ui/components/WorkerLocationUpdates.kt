package com.erno.app.ui.components

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.location.LocationListener
import android.location.LocationManager
import android.os.Build
import android.os.Bundle
import android.os.Looper
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.graphics.Color
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.erno.app.data.repository.ErrnoMobileApi
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.concurrent.atomic.AtomicLong

/** Foreground-only GPS pulses. The screen lifecycle owns provider registration; no background service is started. */
@Composable
fun WorkerLocationUpdates(available: Boolean, activeJobId: String?, modifier: Modifier = Modifier) {
    val context= LocalContext.current
    val lifecycle= LocalLifecycleOwner.current.lifecycle
    var denied by remember { mutableStateOf(false) }
    var permissionReady by remember { mutableStateOf(hasLocationPermission(context)) }
    val permission=rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) { grants ->
        permissionReady=grants.values.any { it } || hasLocationPermission(context)
        denied=!permissionReady
    }
    val active=available || activeJobId != null
    LaunchedEffect(active,permissionReady) { if(active && !permissionReady) permission.launch(arrayOf(Manifest.permission.ACCESS_FINE_LOCATION,Manifest.permission.ACCESS_COARSE_LOCATION)) }
    DisposableEffect(active,permissionReady,lifecycle,activeJobId) {
        if(!active || !permissionReady) return@DisposableEffect onDispose {}
        val manager=context.getSystemService(Context.LOCATION_SERVICE) as LocationManager
        val scope=CoroutineScope(SupervisorJob()+Dispatchers.IO)
        val lastSent=AtomicLong(0)
        val listener=object:LocationListener {
            override fun onLocationChanged(location: Location) {
                val age=System.currentTimeMillis()-location.time
                if(age>120_000 || !location.latitude.isFinite() || !location.longitude.isFinite() || location.accuracy>250f) return
                val minimum=if(activeJobId!=null) 5_000L else 30_000L
                val now=System.currentTimeMillis(); val previous=lastSent.get()
                if(now-previous<minimum || !lastSent.compareAndSet(previous,now)) return
                scope.launch {
                    var waitMs=1000L
                    repeat(4) { attempt ->
                        try {
                            if(activeJobId!=null) ErrnoMobileApi.updateAssignedLocation(activeJobId,location.latitude,location.longitude)
                            else ErrnoMobileApi.updateAvailableLocation(location.latitude,location.longitude)
                            return@launch
                        } catch (_:Exception) { if(attempt<3){ delay(waitMs); waitMs=(waitMs*2).coerceAtMost(8000L) } }
                    }
                }
            }
            @Deprecated("Deprecated in Android") override fun onStatusChanged(provider:String?,status:Int,extras:Bundle?) {}
            override fun onProviderEnabled(provider:String) {}
            override fun onProviderDisabled(provider:String) {}
        }
        fun begin() {
            try {
                val providers=manager.getProviders(true).filter { it==LocationManager.GPS_PROVIDER || it==LocationManager.NETWORK_PROVIDER }
                providers.forEach { provider ->
                    val interval=if(activeJobId!=null) 8_000L else 45_000L
                    manager.requestLocationUpdates(provider,interval,if(activeJobId!=null) 10f else 75f,listener,Looper.getMainLooper())
                    manager.getLastKnownLocation(provider)?.let(listener::onLocationChanged)
                }
            } catch (_:SecurityException) { denied=true }
        }
        val observer=LifecycleEventObserver { _, event -> when(event){Lifecycle.Event.ON_START->begin();Lifecycle.Event.ON_STOP->manager.removeUpdates(listener);else->Unit} }
        lifecycle.addObserver(observer)
        if(lifecycle.currentState.isAtLeast(Lifecycle.State.STARTED)) begin()
        onDispose { lifecycle.removeObserver(observer); manager.removeUpdates(listener); scope.cancel() }
    }
    if(denied) Text("Location permission is off. Turn it on to share location while available or on an active job.",color=Color(0xFFB3261E),modifier=modifier)
}
private fun hasLocationPermission(context:Context)=ContextCompat.checkSelfPermission(context,Manifest.permission.ACCESS_FINE_LOCATION)==PackageManager.PERMISSION_GRANTED || ContextCompat.checkSelfPermission(context,Manifest.permission.ACCESS_COARSE_LOCATION)==PackageManager.PERMISSION_GRANTED

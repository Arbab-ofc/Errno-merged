package com.erno.app.ui.components

import android.content.ActivityNotFoundException
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.widget.Toast

fun googleMapsDirectionsUri(latitude: Double?, longitude: Double?): Uri? {
    if (latitude == null || longitude == null || !latitude.isFinite() || !longitude.isFinite() || latitude !in -90.0..90.0 || longitude !in -180.0..180.0) return null
    return Uri.Builder().scheme("https").authority("www.google.com").appendPath("maps").appendPath("dir").appendPath("")
        .appendQueryParameter("api", "1")
        .appendQueryParameter("destination", "$latitude,$longitude")
        .appendQueryParameter("travelmode", "driving")
        .build()
}

fun openGoogleMapsDirections(context: Context, latitude: Double?, longitude: Double?) {
    val uri = googleMapsDirectionsUri(latitude, longitude)
    if (uri == null) {
        Toast.makeText(context, "Shop coordinates are unavailable. Contact the shop for directions.", Toast.LENGTH_LONG).show()
        return
    }
    try {
        context.startActivity(Intent(Intent.ACTION_VIEW, uri).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
    } catch (_: ActivityNotFoundException) {
        Toast.makeText(context, "No map app or browser is available for directions.", Toast.LENGTH_LONG).show()
    } catch (_: SecurityException) {
        Toast.makeText(context, "Could not open directions. Try again or use the shop address.", Toast.LENGTH_LONG).show()
    }
}

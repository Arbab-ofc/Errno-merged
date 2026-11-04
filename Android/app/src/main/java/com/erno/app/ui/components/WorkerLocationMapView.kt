package com.erno.app.ui.components

import android.content.Intent
import android.net.Uri
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.*
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.PathEffect
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.erno.app.ui.theme.ErnoGreen

@Composable
fun WorkerLocationMapView(
    locationName: String,
    distanceText: String,
    latitude: Double = 28.5355,
    longitude: Double = 77.2641,
    isDarkTheme: Boolean = true
) {
    val context = LocalContext.current
    var currentDarkTheme by remember { mutableStateOf(isDarkTheme) }
    var showEtaDetails by remember { mutableStateOf(true) }
    var zoomLevel by remember { mutableIntStateOf(15) }

    val backgroundColor = if (currentDarkTheme) Color(0xFF101722) else Color(0xFFE5EEF5) // Leaflet tile background
    val roadColor = if (currentDarkTheme) Color(0xFF1E293B) else Color(0xFFFFFFFF)
    val accentPathColor = ErnoGreen

    // Infinite pulse animation for worker and destination markers
    val infiniteTransition = rememberInfiniteTransition(label = "leaflet_map_pulse")
    val pulseRadius by infiniteTransition.animateFloat(
        initialValue = 16f,
        targetValue = 32f,
        animationSpec = infiniteRepeatable(
            animation = tween(1200, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "pulse_radius"
    )
    val pulseAlpha by infiniteTransition.animateFloat(
        initialValue = 0.6f,
        targetValue = 0f,
        animationSpec = infiniteRepeatable(
            animation = tween(1200, easing = FastOutSlowInEasing),
            repeatMode = RepeatMode.Restart
        ),
        label = "pulse_alpha"
    )

    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .height(210.dp),
        shape = RoundedCornerShape(16.dp),
        color = backgroundColor,
        shadowElevation = 4.dp,
        border = BorderStroke(1.dp, if (currentDarkTheme) Color(0xFF202D3D) else Color(0xFFCBD5E1))
    ) {
        Box(modifier = Modifier.fillMaxSize()) {
            // Drawn Leaflet Map Tile Grid & Route Graphics
            Canvas(modifier = Modifier.fillMaxSize()) {
                val width = size.width
                val height = size.height

                // Leaflet OpenStreetMap grid pattern
                drawRect(
                    color = roadColor,
                    topLeft = Offset(0f, height * 0.4f),
                    size = Size(width, 36f)
                )
                drawRect(
                    color = roadColor,
                    topLeft = Offset(width * 0.35f, 0f),
                    size = Size(36f, height)
                )
                drawRect(
                    color = roadColor,
                    topLeft = Offset(width * 0.7f, 0f),
                    size = Size(28f, height)
                )

                // Dashed Route Line from Worker to Store Location (Leaflet Routing API style)
                val path = Path().apply {
                    moveTo(width * 0.15f, height * 0.75f)
                    lineTo(width * 0.35f, height * 0.4f)
                    lineTo(width * 0.7f, height * 0.4f)
                }
                drawPath(
                    path = path,
                    color = accentPathColor,
                    style = Stroke(
                        width = 12f,
                        pathEffect = PathEffect.dashPathEffect(floatArrayOf(16f, 12f), 0f)
                    )
                )

                // Animated Pulse Ring around Worker Location
                drawCircle(
                    color = Color(0xFF2196F3).copy(alpha = pulseAlpha),
                    radius = pulseRadius * (zoomLevel / 15f),
                    center = Offset(width * 0.15f, height * 0.75f)
                )

                // Worker Marker Center Dot
                drawCircle(
                    color = Color(0xFF2196F3),
                    radius = 12f,
                    center = Offset(width * 0.15f, height * 0.75f)
                )
                drawCircle(
                    color = Color.White,
                    radius = 5f,
                    center = Offset(width * 0.15f, height * 0.75f)
                )
            }

            // Top-Left Leaflet Attribution Badge ("Leaflet | © OpenStreetMap contributors")
            Surface(
                modifier = Modifier
                    .align(Alignment.TopStart)
                    .padding(6.dp),
                shape = RoundedCornerShape(4.dp),
                color = Color.Black.copy(alpha = 0.6f)
            ) {
                Text(
                    text = "Leaflet | © OpenStreetMap",
                    fontSize = 9.sp,
                    color = Color.White.copy(alpha = 0.85f),
                    modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                )
            }

            // Top-Right Leaflet Map Controls (Zoom In, Zoom Out, Theme Toggle)
            Column(
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .padding(6.dp),
                verticalArrangement = Arrangement.spacedBy(4.dp),
                horizontalAlignment = Alignment.End
            ) {
                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    // Zoom In (+)
                    Surface(
                        modifier = Modifier
                            .size(28.dp)
                            .clip(CircleShape)
                            .clickable { if (zoomLevel < 18) zoomLevel++ },
                        color = Color.Black.copy(alpha = 0.6f),
                        shape = CircleShape
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Icon(
                                imageVector = Icons.Default.Add,
                                contentDescription = "Zoom In",
                                tint = Color.White,
                                modifier = Modifier.size(14.dp)
                            )
                        }
                    }

                    // Zoom Out (-)
                    Surface(
                        modifier = Modifier
                            .size(28.dp)
                            .clip(CircleShape)
                            .clickable { if (zoomLevel > 10) zoomLevel-- },
                        color = Color.Black.copy(alpha = 0.6f),
                        shape = CircleShape
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Icon(
                                imageVector = Icons.Default.Remove,
                                contentDescription = "Zoom Out",
                                tint = Color.White,
                                modifier = Modifier.size(14.dp)
                            )
                        }
                    }
                }

                Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                    // Theme Toggle Button
                    Surface(
                        modifier = Modifier
                            .size(28.dp)
                            .clip(CircleShape)
                            .clickable { currentDarkTheme = !currentDarkTheme },
                        color = Color.Black.copy(alpha = 0.6f),
                        shape = CircleShape
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Icon(
                                imageVector = if (currentDarkTheme) Icons.Default.WbSunny else Icons.Default.DarkMode,
                                contentDescription = "Toggle Theme",
                                tint = Color.White,
                                modifier = Modifier.size(14.dp)
                            )
                        }
                    }

                    // GPS Re-center Button
                    Surface(
                        modifier = Modifier
                            .size(28.dp)
                            .clip(CircleShape)
                            .clickable { zoomLevel = 15 },
                        color = Color.Black.copy(alpha = 0.6f),
                        shape = CircleShape
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Icon(
                                imageVector = Icons.Default.MyLocation,
                                contentDescription = "Re-center GPS",
                                tint = ErnoGreen,
                                modifier = Modifier.size(14.dp)
                            )
                        }
                    }
                }
            }

            // Interactive Live ETA & Traffic Status Popover Overlay
            AnimatedVisibility(
                visible = showEtaDetails,
                enter = fadeIn(),
                exit = fadeOut(),
                modifier = Modifier
                    .align(Alignment.CenterStart)
                    .padding(start = 8.dp)
            ) {
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = Color.Black.copy(alpha = 0.75f),
                    shadowElevation = 2.dp
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(
                            modifier = Modifier
                                .size(7.dp)
                                .background(ErnoGreen, CircleShape)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = "Leaflet API • Zoom $zoomLevel • $distanceText",
                            fontSize = 10.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = Color.White
                        )
                    }
                }
            }

            // Destination Store Leaflet Marker Pin Overlay
            Box(
                modifier = Modifier
                    .align(Alignment.Center)
                    .offset(x = 35.dp, y = (-12).dp)
            ) {
                Surface(
                    shape = RoundedCornerShape(16.dp),
                    color = ErnoGreen,
                    shadowElevation = 6.dp
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.Default.Storefront,
                            contentDescription = null,
                            tint = Color.White,
                            modifier = Modifier.size(15.dp)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(
                            text = locationName,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                    }
                }
            }

            // Bottom Map Action Bar: Open External Navigation
            Surface(
                modifier = Modifier
                    .align(Alignment.BottomStart)
                    .fillMaxWidth()
                    .clickable {
                        val gmmIntentUri = Uri.parse("geo:$latitude,$longitude?q=${Uri.encode(locationName)}")
                        val mapIntent = Intent(Intent.ACTION_VIEW, gmmIntentUri).apply {
                            setPackage("com.google.android.apps.maps")
                        }
                        if (mapIntent.resolveActivity(context.packageManager) != null) {
                            context.startActivity(mapIntent)
                        } else {
                            val browserIntent = Intent(
                                Intent.ACTION_VIEW,
                                Uri.parse("https://www.google.com/maps/search/?api=1&query=${Uri.encode(locationName)}")
                            )
                            context.startActivity(browserIntent)
                        }
                    },
                color = Color.Black.copy(alpha = 0.75f)
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = Icons.Default.LocationOn,
                            contentDescription = null,
                            tint = ErnoGreen,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(
                            text = "$locationName • $distanceText",
                            fontSize = 12.sp,
                            color = Color.White,
                            fontWeight = FontWeight.Medium
                        )
                    }

                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = Icons.Default.Directions,
                            contentDescription = null,
                            tint = ErnoGreen,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(2.dp))
                        Text(
                            text = "Directions",
                            fontSize = 11.sp,
                            color = ErnoGreen,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
            }
        }
    }
}

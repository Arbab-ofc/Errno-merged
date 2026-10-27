package com.erno.app.ui.components

import android.content.Intent
import android.net.Uri
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.*
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
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

    val backgroundColor = if (currentDarkTheme) Color(0xFF131D2A) else Color(0xFFE8ECEF)
    val roadColor = if (currentDarkTheme) Color(0xFF202D3D) else Color(0xFFFFFFFF)
    val accentPathColor = ErnoGreen

    // Infinite pulse animation for worker and destination markers
    val infiniteTransition = rememberInfiniteTransition(label = "map_pulse")
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
            .height(200.dp)
            .clickable { showEtaDetails = !showEtaDetails },
        shape = RoundedCornerShape(16.dp),
        color = backgroundColor,
        shadowElevation = 4.dp
    ) {
        Box(modifier = Modifier.fillMaxSize()) {
            // Drawn Map Grid & Route Graphics
            Canvas(modifier = Modifier.fillMaxSize()) {
                val width = size.width
                val height = size.height

                // Background grid pattern / secondary roads
                drawRect(
                    color = roadColor,
                    topLeft = Offset(0f, height * 0.4f),
                    size = Size(width, 32f)
                )
                drawRect(
                    color = roadColor,
                    topLeft = Offset(width * 0.35f, 0f),
                    size = Size(32f, height)
                )
                drawRect(
                    color = roadColor,
                    topLeft = Offset(width * 0.7f, 0f),
                    size = Size(24f, height)
                )

                // Dashed Route Line from Worker to Store Location
                val path = Path().apply {
                    moveTo(width * 0.15f, height * 0.75f)
                    lineTo(width * 0.35f, height * 0.4f)
                    lineTo(width * 0.7f, height * 0.4f)
                }
                drawPath(
                    path = path,
                    color = accentPathColor,
                    style = Stroke(
                        width = 10f,
                        pathEffect = PathEffect.dashPathEffect(floatArrayOf(16f, 12f), 0f)
                    )
                )

                // Animated Pulse Ring around Worker Location
                drawCircle(
                    color = Color(0xFF2196F3).copy(alpha = pulseAlpha),
                    radius = pulseRadius,
                    center = Offset(width * 0.15f, height * 0.75f)
                )

                // Worker Location Center Dot
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

            // Top Interactive Controls Overlay (Theme Toggle & Re-center button)
            Row(
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .padding(8.dp),
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                // Theme Toggle Button
                Surface(
                    modifier = Modifier
                        .size(32.dp)
                        .clip(CircleShape)
                        .clickable { currentDarkTheme = !currentDarkTheme },
                    color = Color.Black.copy(alpha = 0.5f),
                    shape = CircleShape
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(
                            imageVector = if (currentDarkTheme) Icons.Default.WbSunny else Icons.Default.DarkMode,
                            contentDescription = "Toggle Theme",
                            tint = Color.White,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                }

                // GPS Re-center / Refresh Button
                Surface(
                    modifier = Modifier
                        .size(32.dp)
                        .clip(CircleShape)
                        .clickable { showEtaDetails = !showEtaDetails },
                    color = Color.Black.copy(alpha = 0.5f),
                    shape = CircleShape
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(
                            imageVector = Icons.Default.MyLocation,
                            contentDescription = "Refresh Location",
                            tint = ErnoGreen,
                            modifier = Modifier.size(16.dp)
                        )
                    }
                }
            }

            // Interactive Live ETA & Traffic Status Popover Overlay
            AnimatedVisibility(
                visible = showEtaDetails,
                enter = fadeIn(),
                exit = fadeOut(),
                modifier = Modifier
                    .align(Alignment.TopStart)
                    .padding(8.dp)
            ) {
                Surface(
                    shape = RoundedCornerShape(10.dp),
                    color = Color.Black.copy(alpha = 0.75f),
                    shadowElevation = 2.dp
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(
                            modifier = Modifier
                                .size(8.dp)
                                .background(ErnoGreen, CircleShape)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text(
                            text = "Live • Clear Route • $distanceText",
                            fontSize = 10.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = Color.White
                        )
                    }
                }
            }

            // Destination Store Marker Overlay
            Box(
                modifier = Modifier
                    .align(Alignment.Center)
                    .offset(x = 40.dp, y = (-10).dp)
            ) {
                Surface(
                    shape = RoundedCornerShape(20.dp),
                    color = ErnoGreen,
                    shadowElevation = 6.dp
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.Default.Storefront,
                            contentDescription = null,
                            tint = Color.White,
                            modifier = Modifier.size(16.dp)
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

            // Bottom Map Action Bar: Open Google Maps
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
                color = Color.Black.copy(alpha = 0.7f)
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
                            text = "Open in Maps",
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

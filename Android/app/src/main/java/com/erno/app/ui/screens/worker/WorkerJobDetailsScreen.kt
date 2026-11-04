package com.erno.app.ui.screens.worker

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.erno.app.ui.components.WorkerLocationMapView
import com.erno.app.ui.theme.ErnoGreen
import com.erno.app.ui.theme.ErnoTextSecondary

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WorkerJobDetailsScreen(
    state: WorkerState,
    onBackClick: () -> Unit,
    onDurationSelect: (hours: Int, pay: Int) -> Unit,
    onAcceptJobClick: () -> Unit
) {
    val job = state.selectedJob ?: state.availableJobs.first()
    var selectedHours by remember { mutableIntStateOf(job.selectedHours) }

    val isAlreadyAccepted = job.status == "Ongoing" || job.status == "Accepted" || job.status == "Upcoming" || job.status == "Completed"

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "Job Details",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back",
                            tint = Color.White
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color(0xFF0B121F))
            )
        },
        bottomBar = {
            Surface(
                color = Color(0xFF0B121F),
                tonalElevation = 8.dp
            ) {
                Box(modifier = Modifier.padding(16.dp)) {
                    if (!isAlreadyAccepted) {
                        Button(
                            onClick = onAcceptJobClick,
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(52.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = ErnoGreen),
                            shape = RoundedCornerShape(12.dp)
                        ) {
                            Text(
                                text = "Accept Job",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.White
                            )
                        }
                    } else {
                        Surface(
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(52.dp),
                            shape = RoundedCornerShape(12.dp),
                            color = when (job.status) {
                                "Ongoing" -> Color(0xFF1B4D3E)
                                "Completed" -> Color(0xFF263238)
                                else -> Color(0xFF1E293B)
                            }
                        ) {
                            Box(
                                modifier = Modifier.fillMaxSize(),
                                contentAlignment = Alignment.Center
                            ) {
                                Text(
                                    text = when (job.status) {
                                        "Ongoing" -> "Active Shift (Job Ongoing)"
                                        "Completed" -> "Shift Completed"
                                        else -> "Job Already Accepted"
                                    },
                                    fontSize = 15.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = if (job.status == "Ongoing") ErnoGreen else Color.White
                                )
                            }
                        }
                    }
                }
            }
        },
        containerColor = Color(0xFF0B121F)
    ) { paddingValues ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(horizontal = 20.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Main Details Container
            item {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(20.dp),
                    color = Color.White
                ) {
                    Column(modifier = Modifier.padding(20.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = job.title,
                                fontSize = 20.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.Black
                            )

                            if (isAlreadyAccepted) {
                                Surface(
                                    shape = RoundedCornerShape(8.dp),
                                    color = when (job.status) {
                                        "Ongoing" -> Color(0xFFFFF3E0)
                                        "Completed" -> Color(0xFFE8F5E9)
                                        else -> Color(0xFFEAF5D8)
                                    }
                                ) {
                                    Text(
                                        text = job.status,
                                        fontSize = 12.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = when (job.status) {
                                            "Ongoing" -> Color(0xFFE65100)
                                            "Completed" -> Color(0xFF2E7D32)
                                            else -> ErnoGreen
                                        },
                                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                                    )
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(4.dp))

                        val isPreBooking = job.bookingType == "PRE_BOOKING"
                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = if (isPreBooking) Color(0xFFE3F2FD) else Color(0xFFEAF5D8)
                        ) {
                            Text(
                                text = if (isPreBooking) "Pre-Booking • Date: ${job.scheduledDate} (${job.scheduledTime})" else "Current Job • Today (${job.scheduledDate})",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold,
                                color = if (isPreBooking) Color(0xFF1565C0) else ErnoGreen,
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                            )
                        }

                        Spacer(modifier = Modifier.height(8.dp))

                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.Default.LocationOn,
                                contentDescription = null,
                                tint = Color.Gray,
                                modifier = Modifier.size(16.dp)
                            )
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(
                                text = "${job.location} • ${job.distance}",
                                fontSize = 13.sp,
                                color = Color.Gray
                            )
                        }

                        Spacer(modifier = Modifier.height(16.dp))

                        Text(
                            text = "Job Description:",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.Black
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = job.description,
                            fontSize = 14.sp,
                            color = ErnoTextSecondary,
                            lineHeight = 20.sp
                        )

                        if (job.requirements.isNotBlank()) {
                            Spacer(modifier = Modifier.height(12.dp))
                            Text(
                                text = "Job Requirements:",
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.Black
                            )
                            Spacer(modifier = Modifier.height(2.dp))
                            Text(
                                text = job.requirements,
                                fontSize = 14.sp,
                                color = ErnoTextSecondary,
                                lineHeight = 20.sp
                            )
                        }

                        Spacer(modifier = Modifier.height(20.dp))

                        // Interactive Map View showing store location & route
                        Text(
                            text = "Work Location & Route",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.Black
                        )

                        Spacer(modifier = Modifier.height(8.dp))

                        WorkerLocationMapView(
                            locationName = job.location,
                            distanceText = job.distance,
                            latitude = job.latitude,
                            longitude = job.longitude,
                            isDarkTheme = true
                        )

                        Spacer(modifier = Modifier.height(24.dp))

                        Text(
                            text = "Choose Duration & Pay",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.Black
                        )
                        Text(
                            text = "Select the time you can work",
                            fontSize = 12.sp,
                            color = Color.Gray
                        )

                        Spacer(modifier = Modifier.height(12.dp))

                        job.payStructure.forEach { option ->
                            val isSelected = selectedHours == option.hours
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable {
                                        if (!isAlreadyAccepted) {
                                            selectedHours = option.hours
                                            onDurationSelect(option.hours, option.price)
                                        }
                                    }
                                    .padding(vertical = 10.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = "${option.hours} Hour${if (option.hours > 1) "s" else ""}",
                                    fontSize = 14.sp,
                                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                    color = Color.Black
                                )

                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text(
                                        text = "₹${option.price}",
                                        fontSize = 14.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = Color.Black
                                    )
                                    Spacer(modifier = Modifier.width(12.dp))
                                    RadioButton(
                                        selected = isSelected,
                                        onClick = {
                                            if (!isAlreadyAccepted) {
                                                selectedHours = option.hours
                                                onDurationSelect(option.hours, option.price)
                                            }
                                        },
                                        colors = RadioButtonDefaults.colors(selectedColor = ErnoGreen),
                                        enabled = !isAlreadyAccepted
                                    )
                                }
                            }
                            HorizontalDivider(color = Color(0xFFF5F5F5))
                        }
                    }
                }
            }
        }
    }
}

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
import com.erno.app.data.repository.ErrnoMobileApi

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WorkerJobDetailsScreen(
    state: WorkerState,
    onBackClick: () -> Unit,
    onDurationSelect: (hours: Int, pay: Int) -> Unit,
    onAcceptJobClick: () -> Unit,
    onStartJobClick: () -> Unit = {}
) {
    val job = state.selectedJob ?: state.availableJobs.firstOrNull()
    if (job == null) {
        Scaffold(containerColor = Color(0xFF0B121F)) { padding ->
            Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                Text("Job unavailable. Refresh the marketplace and try again.", color = Color.White)
            }
        }
        return
    }
    var selectedHours by remember { mutableIntStateOf(job.selectedHours) }
    var payoutText by remember(job.id) { mutableStateOf<String?>(null) }
    var payoutError by remember(job.id) { mutableStateOf<String?>(null) }
    LaunchedEffect(job.id) {
        runCatching { ErrnoMobileApi.workerPayout(job.id) }
            .onSuccess { payoutText = it.optString("worker_payout_amount").takeIf(String::isNotBlank) }
            .onFailure { payoutError = it.localizedMessage ?: "Worker payout is unavailable for this legacy job." }
    }

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
            if (job.status == "Available") Surface(
                color = Color(0xFF0B121F),
                tonalElevation = 8.dp
            ) {
                Box(modifier = Modifier.padding(16.dp)) {
                    Button(
                        onClick = onAcceptJobClick,
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(52.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = ErnoGreen),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Text(
                            text = "Apply for Job",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                    }
                }
            } else if (job.status == "Upcoming") Surface(color = Color(0xFF0B121F)) {
                Button(onClick = onStartJobClick, enabled = !state.lifecycleActionLoading, modifier = Modifier.fillMaxWidth().padding(16.dp).height(52.dp), colors = ButtonDefaults.buttonColors(containerColor = ErnoGreen)) {
                    Text(if (state.lifecycleActionLoading) "Starting…" else "Start Job", color = Color.White, fontWeight = FontWeight.Bold)
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
            if (state.jobLoadError != null) item { Text(state.jobLoadError.orEmpty(), color = Color(0xFFFF8A80)) }
            // Main Details Container
            item {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(20.dp),
                    color = Color.White
                ) {
                    Column(modifier = Modifier.padding(20.dp)) {
                        Text(
                            text = job.title,
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.Black
                        )
                        Text("Status: ${job.status}", fontSize = 12.sp, color = ErnoGreen, fontWeight = FontWeight.SemiBold)

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
                            Text("Job Requirements:", fontSize = 14.sp, fontWeight = FontWeight.Bold, color = Color.Black)
                            Spacer(modifier = Modifier.height(2.dp))
                            Text(job.requirements, fontSize = 14.sp, color = ErnoTextSecondary, lineHeight = 20.sp)
                        }

                        Surface(color = Color(0xFF182436), shape = RoundedCornerShape(12.dp), modifier = Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                                Text("Expected earnings", color = Color.White, fontWeight = FontWeight.Bold)
                                Text("Duration: ${job.selectedHours} hour(s)", color = Color.White.copy(alpha = .8f), fontSize = 12.sp)
                                Text("Customer service charge: ₹${job.selectedPay}", color = Color.White.copy(alpha = .8f), fontSize = 12.sp)
                                Text("Worker payout: ${payoutText?.let { "₹$it" } ?: payoutError ?: "Loading…"}", color = ErnoGreen, fontWeight = FontWeight.Bold)
                                Text("Settlement status: Not provided by the payment service", color = Color.White.copy(alpha = .65f), fontSize = 11.sp)
                            }
                        }
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
                                        selectedHours = option.hours
                                        onDurationSelect(option.hours, option.price)
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
                                            selectedHours = option.hours
                                            onDurationSelect(option.hours, option.price)
                                        },
                                        colors = RadioButtonDefaults.colors(selectedColor = ErnoGreen)
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

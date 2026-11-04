package com.erno.app.ui.screens.shopkeeper

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
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
fun PreviewJobScreen(
    state: ShopkeeperState,
    onBackClick: () -> Unit,
    onEditClick: () -> Unit,
    onPostJobClick: () -> Unit
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "Preview Job",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.Black
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back",
                            tint = Color.Black
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.White)
            )
        },
        bottomBar = {
            Surface(
                color = Color.White,
                tonalElevation = 8.dp
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    OutlinedButton(
                        onClick = onEditClick,
                        modifier = Modifier
                            .weight(1f)
                            .height(52.dp),
                        shape = RoundedCornerShape(12.dp),
                        border = BorderStroke(1.dp, ErnoGreen)
                    ) {
                        Text(
                            text = "Edit",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            color = ErnoGreen
                        )
                    }

                    Button(
                        onClick = onPostJobClick,
                        enabled = state.pricingQuote["quote_id"] != null,
                        modifier = Modifier
                            .weight(1f)
                            .height(52.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = ErnoGreen),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Text(
                            text = if (state.pricingQuote["quote_id"] != null) "Confirm Job" else "Price unavailable",
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                    }
                }
            }
        },
        containerColor = Color(0xFFF9FAFB)
    ) { paddingValues ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(horizontal = 16.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            item {
                Surface(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(16.dp), color = Color.White,
                    border = BorderStroke(1.dp, Color(0xFFE0E0E0))) {
                    Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                        Text("Backend price quote", fontWeight = FontWeight.Bold, color = Color.Black)
                        Text("Customer charge: ₹${state.pricingQuote["final_service_charge"] ?: "Unavailable"}", fontSize = 18.sp, fontWeight = FontWeight.Bold, color = ErnoGreen)
                        Text("Base ₹${state.pricingQuote["base_price"] ?: "—"} · maximum ₹${state.pricingQuote["maximum_price"] ?: "—"}", fontSize = 12.sp, color = ErnoTextSecondary)
                        Text("Time ${state.pricingQuote["time_multiplier"] ?: "—"}× · demand ${state.pricingQuote["demand_multiplier"] ?: "—"}×", fontSize = 12.sp, color = ErnoTextSecondary)
                        Text("ERRNO commission ₹${state.pricingQuote["commission_amount"] ?: "—"} · worker payout ₹${state.pricingQuote["worker_payout_amount"] ?: "—"}", fontSize = 12.sp, color = ErnoTextSecondary)
                        Text("Quote expires: ${state.pricingQuote["expires_at"] ?: "—"}", fontSize = 11.sp, color = ErnoTextSecondary)
                        if (state.errorMessage != null) Text(state.errorMessage, color = Color(0xFFB3261E), fontSize = 12.sp)
                    }
                }
            }
            item {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    color = Color.White,
                    shadowElevation = 1.dp
                ) {
                    Column(modifier = Modifier.padding(18.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = state.draftTitle.ifBlank { "Loading & Unloading" },
                                fontSize = 20.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.Black
                            )

                            if (state.draftIsDelivery) {
                                Surface(
                                    shape = RoundedCornerShape(8.dp),
                                    color = Color(0xFFE3F2FD)
                                ) {
                                    Text(
                                        text = "Delivery Job",
                                        fontSize = 11.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = Color(0xFF1976D2),
                                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                                    )
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(8.dp))

                        val isPreBooking = state.draftBookingType == "PRE_BOOKING"
                        val timeLabel = if (state.draftWorkingRequirementType == "IMMEDIATE") {
                            if (isPreBooking) "Immediate Start on ${state.draftScheduledDate}" else "Immediate Requirement (Today)"
                        } else {
                            if (isPreBooking) "${state.draftScheduledDate} at ${state.draftScheduledTime}" else "Today at ${state.draftScheduledTime}"
                        }

                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = if (isPreBooking) Color(0xFFE3F2FD) else Color(0xFFEAF5D8),
                            border = BorderStroke(1.dp, if (isPreBooking) Color(0xFF1565C0) else ErnoGreen)
                        ) {
                            Text(
                                text = if (isPreBooking) "Pre-Booking • $timeLabel" else "Current Job • $timeLabel",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold,
                                color = if (isPreBooking) Color(0xFF1565C0) else ErnoGreen,
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp)
                            )
                        }

                        Spacer(modifier = Modifier.height(10.dp))

                        Text(
                            text = "Workers Required: ${state.draftWorkerCount} Worker${if (state.draftWorkerCount > 1) "s" else ""}",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.SemiBold,
                            color = Color.Black
                        )

                        Spacer(modifier = Modifier.height(6.dp))

                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.Default.LocationOn,
                                contentDescription = null,
                                tint = Color.Gray,
                                modifier = Modifier.size(16.dp)
                            )
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(
                                text = state.draftLocation.ifBlank { "Okhla Market Area" },
                                fontSize = 13.sp,
                                color = Color.Gray
                            )
                        }

                        // Delivery Pickup & Drop-off Route (ONLY FOR DELIVERY JOBS)
                        if (state.draftIsDelivery) {
                            Spacer(modifier = Modifier.height(10.dp))
                            Surface(
                                shape = RoundedCornerShape(10.dp),
                                color = Color(0xFFF8F9FA),
                                border = BorderStroke(1.dp, Color(0xFFE0E0E0))
                            ) {
                                Column(modifier = Modifier.padding(10.dp)) {
                                    Text(
                                        text = "Pickup: ${state.draftPickupLocation.ifBlank { "Okhla Market Store #12" }}",
                                        fontSize = 12.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = Color.Black
                                    )
                                    Spacer(modifier = Modifier.height(3.dp))
                                    Text(
                                        text = "Drop: ${state.draftDropLocation.ifBlank { "Sector 18 Noida Address" }}",
                                        fontSize = 12.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = Color.Black
                                    )
                                }
                            }
                        }

                        Spacer(modifier = Modifier.height(12.dp))

                        // Interactive Shop Location Map Preview
                        WorkerLocationMapView(
                            locationName = if (state.draftIsDelivery) state.draftPickupLocation else state.draftLocation.ifBlank { "Okhla Market Area" },
                            distanceText = "Location Map Preview",
                            isDarkTheme = false
                        )

                        Spacer(modifier = Modifier.height(14.dp))

                        Text(
                            text = "Job Description:",
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.Black
                        )
                        Spacer(modifier = Modifier.height(2.dp))
                        Text(
                            text = state.draftDescription.ifBlank { "Workers are required for loading and unloading goods." },
                            fontSize = 13.sp,
                            color = ErnoTextSecondary,
                            lineHeight = 18.sp
                        )

                        Spacer(modifier = Modifier.height(12.dp))

                        if (state.draftRequirements.isNotBlank()) {
                            Text(
                                text = "Job Requirements:",
                                fontSize = 13.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.Black
                            )
                            Spacer(modifier = Modifier.height(2.dp))
                            Text(
                                text = state.draftRequirements,
                                fontSize = 13.sp,
                                color = ErnoTextSecondary,
                                lineHeight = 18.sp
                            )
                            Spacer(modifier = Modifier.height(14.dp))
                        }

                        Row(
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = "Pay Structure & Duration",
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.Black
                            )
                        }

                        Spacer(modifier = Modifier.height(8.dp))

                        state.draftPayStructure.forEach { item ->
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(vertical = 6.dp),
                                horizontalArrangement = Arrangement.SpaceBetween
                            ) {
                                Text(
                                    text = "${item.hours} Hour${if (item.hours > 1) "s" else ""} Shift",
                                    fontSize = 13.sp,
                                    color = Color.Black
                                )
                                Text(
                                    text = "₹${item.price}",
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color.Black
                                )
                            }
                            HorizontalDivider(color = Color(0xFFF5F5F5))
                        }
                    }
                }
            }
        }
    }
}

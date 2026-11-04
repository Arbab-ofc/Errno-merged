package com.erno.app.ui.screens.shopkeeper

import android.app.TimePickerDialog
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.AccessTime
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.CalendarToday
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.FlashOn
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.MyLocation
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.erno.app.data.model.DurationPay
import com.erno.app.ui.components.WorkerLocationMapView
import com.erno.app.ui.theme.ErnoGreen
import com.erno.app.ui.theme.ErnoTextSecondary
import java.util.Calendar
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PostJobScreen(
    state: ShopkeeperState,
    onBackClick: () -> Unit,
    onCategoryChange: (String) -> Unit,
    onLocationChange: (String) -> Unit,
    onScheduledDateChange: (String) -> Unit = {},
    onScheduledTimeChange: (String) -> Unit = {},
    onWorkingRequirementTypeChange: (String) -> Unit = {},
    onBookingTypeChange: (String) -> Unit = {},
    onPickupLocationChange: (String) -> Unit = {},
    onDropLocationChange: (String) -> Unit = {},
    onDescriptionChange: (String) -> Unit,
    onRemoveDuration: (DurationPay) -> Unit,
    onToggleDuration: (hours: Int, price: Int) -> Unit = { _, _ -> },
    onAddMoreDurationClick: () -> Unit,
    onPreviewJobClick: () -> Unit
) {
    var currentStep by remember { mutableIntStateOf(1) } // Step 1: Details, Step 2: Duration, Step 3: Location
    var categoryExpanded by remember { mutableStateOf(false) }

    val context = LocalContext.current

    val categories = listOf(
        "Loading & Unloading",
        "Delivery Partner",
        "Shop Helper",
        "Counter Staff",
        "Store Assistant",
        "Packing Staff",
        "Delivery Boy",
        "Cashier"
    )

    val preBookingAvailableDates = remember { getAvailablePreBookingDates() }

    // Native Android TimePickerDialog launch helper
    val timePickerDialog = remember(context) {
        val calendar = Calendar.getInstance()
        val currentHour = calendar.get(Calendar.HOUR_OF_DAY)
        val currentMinute = calendar.get(Calendar.MINUTE)

        TimePickerDialog(
            context,
            { _, hourOfDay, minute ->
                val isPm = hourOfDay >= 12
                val hour12 = when {
                    hourOfDay == 0 -> 12
                    hourOfDay > 12 -> hourOfDay - 12
                    else -> hourOfDay
                }
                val formattedTime = String.format(Locale.US, "%02d:%02d %s", hour12, minute, if (isPm) "PM" else "AM")
                onScheduledTimeChange(formattedTime)
            },
            currentHour,
            currentMinute,
            false // 12-hour AM/PM mode
        )
    }

    // Combined duration list containing standard options + any custom user-added duration option
    val allDurationOptions = remember(state.pricingOptions) {
        state.pricingOptions.sortedBy { it.hours }
    }

    val isStep1Valid = if (state.draftBookingType == "CURRENT") {
        state.draftWorkingRequirementType == "IMMEDIATE" || (state.draftScheduledTime.isNotBlank() && state.draftScheduledTime != "Immediate")
    } else {
        state.draftScheduledDate.isNotBlank() && state.draftScheduledTime.isNotBlank() && state.draftScheduledTime != "Immediate"
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            text = "Post a New Job",
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.Black
                        )
                        Text(
                            text = "Step $currentStep of 3 • " + when (currentStep) {
                                1 -> "Job Type & Details"
                                2 -> "Select Duration"
                                else -> "Location & Map"
                            },
                            fontSize = 12.sp,
                            color = ErnoGreen,
                            fontWeight = FontWeight.SemiBold
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = {
                        if (currentStep > 1) {
                            currentStep--
                        } else {
                            onBackClick()
                        }
                    }) {
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
                modifier = Modifier.imePadding(),
                color = Color.White,
                shadowElevation = 8.dp
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(14.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    if (currentStep > 1) {
                        OutlinedButton(
                            onClick = { currentStep-- },
                            modifier = Modifier
                                .weight(1f)
                                .height(50.dp),
                            shape = RoundedCornerShape(12.dp),
                            border = BorderStroke(1.dp, Color(0xFFD0D0D0))
                        ) {
                            Text(
                                text = "Back",
                                fontSize = 15.sp,
                                color = Color.Black,
                                fontWeight = FontWeight.SemiBold
                            )
                        }
                    }

                    Button(
                        enabled = currentStep != 1 || isStep1Valid,
                        onClick = {
                            if (currentStep < 3) {
                                currentStep++
                            } else {
                                onPreviewJobClick()
                            }
                        },
                        modifier = Modifier
                            .weight(1f)
                            .height(50.dp),
                        colors = ButtonDefaults.buttonColors(
                            containerColor = ErnoGreen,
                            disabledContainerColor = Color(0xFFCCCCCC)
                        ),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Text(
                            text = when (currentStep) {
                                1 -> "Next: Duration & Pay"
                                2 -> "Next: Location"
                                else -> "Preview & Post"
                            },
                            fontSize = 15.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                    }
                }
            }
        },
        containerColor = Color(0xFFF9FAFB)
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            // Step Progress Indicator Bar
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(Color.White)
                    .padding(horizontal = 16.dp, vertical = 10.dp),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                val steps = listOf("1. Details", "2. Duration", "3. Location")
                steps.forEachIndexed { index, title ->
                    val stepNum = index + 1
                    val isActive = currentStep >= stepNum
                    Surface(
                        modifier = Modifier.weight(1f),
                        shape = RoundedCornerShape(8.dp),
                        color = if (isActive) Color(0xFFEAF5D8) else Color(0xFFF0F0F0)
                    ) {
                        Box(
                            modifier = Modifier.padding(vertical = 6.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = title,
                                fontSize = 11.sp,
                                fontWeight = if (isActive) FontWeight.Bold else FontWeight.Medium,
                                color = if (isActive) ErnoGreen else Color.Gray
                            )
                        }
                    }
                }
            }

            HorizontalDivider(color = Color(0xFFEFEFEF))

            // Scrollable Content depending on Current Step
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(horizontal = 16.dp, vertical = 8.dp),
                contentAlignment = Alignment.TopCenter
            ) {
                LazyColumn(
                    modifier = Modifier
                        .fillMaxSize()
                        .widthIn(max = 800.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    if (currentStep == 1) {
                        // 1. BOOKING FLOW (Current Job vs Pre-Booking)
                        item {
                            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                Text(
                                    text = "Booking Type",
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color.Black
                                )

                                val isCurrentSelected = state.draftBookingType == "CURRENT"
                                val isPreBookingSelected = state.draftBookingType == "PRE_BOOKING"

                                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                                    // Current Job Card
                                    Surface(
                                        modifier = Modifier
                                            .weight(1f)
                                            .clickable { onBookingTypeChange("CURRENT") },
                                        shape = RoundedCornerShape(12.dp),
                                        color = if (isCurrentSelected) Color(0xFFEAF5D8) else Color.White,
                                        border = BorderStroke(
                                            width = if (isCurrentSelected) 2.dp else 1.dp,
                                            color = if (isCurrentSelected) ErnoGreen else Color(0xFFD0D0D0)
                                        )
                                    ) {
                                        Column(
                                            modifier = Modifier.padding(12.dp),
                                            verticalArrangement = Arrangement.spacedBy(4.dp)
                                        ) {
                                            Row(
                                                verticalAlignment = Alignment.CenterVertically,
                                                horizontalArrangement = Arrangement.SpaceBetween,
                                                modifier = Modifier.fillMaxWidth()
                                            ) {
                                                Row(verticalAlignment = Alignment.CenterVertically) {
                                                    Icon(
                                                        imageVector = Icons.Default.FlashOn,
                                                        contentDescription = null,
                                                        tint = ErnoGreen,
                                                        modifier = Modifier.size(16.dp)
                                                    )
                                                    Spacer(modifier = Modifier.width(4.dp))
                                                    Text(
                                                        text = "Current Job",
                                                        fontSize = 14.sp,
                                                        fontWeight = FontWeight.Bold,
                                                        color = Color.Black
                                                    )
                                                }
                                                if (isCurrentSelected) {
                                                    Icon(
                                                        imageVector = Icons.Default.Check,
                                                        contentDescription = null,
                                                        tint = ErnoGreen,
                                                        modifier = Modifier.size(16.dp)
                                                    )
                                                }
                                            }
                                            Text(
                                                text = "Hire a worker for today.",
                                                fontSize = 11.sp,
                                                color = Color.Gray
                                            )
                                        }
                                    }

                                    // Pre-Booking Card
                                    Surface(
                                        modifier = Modifier
                                            .weight(1f)
                                            .clickable { onBookingTypeChange("PRE_BOOKING") },
                                        shape = RoundedCornerShape(12.dp),
                                        color = if (isPreBookingSelected) Color(0xFFEAF5D8) else Color.White,
                                        border = BorderStroke(
                                            width = if (isPreBookingSelected) 2.dp else 1.dp,
                                            color = if (isPreBookingSelected) ErnoGreen else Color(0xFFD0D0D0)
                                        )
                                    ) {
                                        Column(
                                            modifier = Modifier.padding(12.dp),
                                            verticalArrangement = Arrangement.spacedBy(4.dp)
                                        ) {
                                            Row(
                                                verticalAlignment = Alignment.CenterVertically,
                                                horizontalArrangement = Arrangement.SpaceBetween,
                                                modifier = Modifier.fillMaxWidth()
                                            ) {
                                                Row(verticalAlignment = Alignment.CenterVertically) {
                                                    Icon(
                                                        imageVector = Icons.Default.CalendarToday,
                                                        contentDescription = null,
                                                        tint = Color(0xFF1565C0),
                                                        modifier = Modifier.size(16.dp)
                                                    )
                                                    Spacer(modifier = Modifier.width(4.dp))
                                                    Text(
                                                        text = "Pre-Booking",
                                                        fontSize = 14.sp,
                                                        fontWeight = FontWeight.Bold,
                                                        color = Color.Black
                                                    )
                                                }
                                                if (isPreBookingSelected) {
                                                    Icon(
                                                        imageVector = Icons.Default.Check,
                                                        contentDescription = null,
                                                        tint = ErnoGreen,
                                                        modifier = Modifier.size(16.dp)
                                                    )
                                                }
                                            }
                                            Text(
                                                text = "Book in advance for upcoming date.",
                                                fontSize = 11.sp,
                                                color = Color.Gray
                                            )
                                        }
                                    }
                                }

                                // Date indicator / Date Selector
                                if (state.draftBookingType == "CURRENT") {
                                    Surface(
                                        shape = RoundedCornerShape(10.dp),
                                        color = Color(0xFFF1F8E9),
                                        border = BorderStroke(1.dp, Color(0xFFA5D6A7)),
                                        modifier = Modifier.fillMaxWidth()
                                    ) {
                                        Row(
                                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                                            verticalAlignment = Alignment.CenterVertically,
                                            horizontalArrangement = Arrangement.SpaceBetween
                                        ) {
                                            Row(verticalAlignment = Alignment.CenterVertically) {
                                                Icon(
                                                    imageVector = Icons.Default.CalendarToday,
                                                    contentDescription = null,
                                                    tint = Color(0xFF1B5E20),
                                                    modifier = Modifier.size(14.dp)
                                                )
                                                Spacer(modifier = Modifier.width(6.dp))
                                                Text(
                                                    text = "Date: Today (${getFormattedTodayDate()})",
                                                    fontSize = 12.sp,
                                                    fontWeight = FontWeight.Bold,
                                                    color = Color(0xFF1B5E20)
                                                )
                                            }
                                            Row(verticalAlignment = Alignment.CenterVertically) {
                                                Icon(
                                                    imageVector = Icons.Default.Lock,
                                                    contentDescription = null,
                                                    tint = ErnoGreen,
                                                    modifier = Modifier.size(12.dp)
                                                )
                                                Spacer(modifier = Modifier.width(4.dp))
                                                Text(
                                                    text = "Automatically Set",
                                                    fontSize = 11.sp,
                                                    fontWeight = FontWeight.SemiBold,
                                                    color = ErnoGreen
                                                )
                                            }
                                        }
                                    }
                                } else {
                                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                        Text(
                                            text = "Select Date (Next 7 Days):",
                                            fontSize = 12.sp,
                                            fontWeight = FontWeight.SemiBold,
                                            color = Color.Black
                                        )
                                        LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                            items(preBookingAvailableDates) { (iso, label) ->
                                                val isSelected = state.draftScheduledDate == iso
                                                Surface(
                                                    onClick = { onScheduledDateChange(iso) },
                                                    shape = RoundedCornerShape(10.dp),
                                                    color = if (isSelected) ErnoGreen else Color.White,
                                                    border = BorderStroke(1.dp, if (isSelected) ErnoGreen else Color(0xFFD0D0D0))
                                                ) {
                                                    Column(
                                                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                                                        horizontalAlignment = Alignment.CenterHorizontally
                                                    ) {
                                                        Text(
                                                            text = label.split(",").firstOrNull() ?: "",
                                                            fontSize = 10.sp,
                                                            color = if (isSelected) Color.White.copy(alpha = 0.9f) else Color.Gray
                                                        )
                                                        Text(
                                                            text = label.split(",").lastOrNull()?.trim() ?: label,
                                                            fontSize = 12.sp,
                                                            fontWeight = FontWeight.Bold,
                                                            color = if (isSelected) Color.White else Color.Black
                                                        )
                                                    }
                                                }
                                            }
                                        }
                                        if (state.draftScheduledDate.isBlank()) {
                                            Text(
                                                text = "Select an available date above to proceed.",
                                                color = Color(0xFFD32F2F),
                                                fontSize = 11.sp,
                                                fontWeight = FontWeight.Medium
                                            )
                                        }
                                    }
                                }
                            }
                        }

                        // 2. JOB CATEGORY (Including "Loading & Unloading")
                        item {
                            Column {
                                Text(
                                    text = "Job Category",
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color.Black
                                )
                                Spacer(modifier = Modifier.height(4.dp))
                                ExposedDropdownMenuBox(
                                    expanded = categoryExpanded,
                                    onExpandedChange = { categoryExpanded = !categoryExpanded }
                                ) {
                                    OutlinedTextField(
                                        value = state.draftCategory,
                                        onValueChange = {},
                                        readOnly = true,
                                        trailingIcon = {
                                            Icon(
                                                imageVector = Icons.Default.KeyboardArrowDown,
                                                contentDescription = null,
                                                tint = Color.Black
                                            )
                                        },
                                        textStyle = LocalTextStyle.current.copy(color = Color.Black, fontWeight = FontWeight.Bold),
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .menuAnchor(),
                                        shape = RoundedCornerShape(10.dp),
                                        colors = OutlinedTextFieldDefaults.colors(
                                            focusedTextColor = Color.Black,
                                            unfocusedTextColor = Color.Black,
                                            focusedBorderColor = ErnoGreen,
                                            unfocusedBorderColor = Color(0xFFE0E0E0),
                                            focusedContainerColor = Color.White,
                                            unfocusedContainerColor = Color.White
                                        )
                                    )
                                    ExposedDropdownMenu(
                                        expanded = categoryExpanded,
                                        onDismissRequest = { categoryExpanded = false },
                                        modifier = Modifier.background(Color.White)
                                    ) {
                                        categories.forEach { category ->
                                            DropdownMenuItem(
                                                text = {
                                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                                        Text(
                                                            text = category,
                                                            color = Color.Black,
                                                            fontWeight = if (category == state.draftCategory) FontWeight.Bold else FontWeight.Medium
                                                        )
                                                        if (category == "Loading & Unloading") {
                                                            Spacer(modifier = Modifier.width(6.dp))
                                                            Surface(
                                                                shape = RoundedCornerShape(4.dp),
                                                                color = Color(0xFFFFF3E0)
                                                            ) {
                                                                Text(
                                                                    text = "Popular",
                                                                    fontSize = 9.sp,
                                                                    fontWeight = FontWeight.Bold,
                                                                    color = Color(0xFFE65100),
                                                                    modifier = Modifier.padding(horizontal = 4.dp, vertical = 1.dp)
                                                                )
                                                            }
                                                        }
                                                    }
                                                },
                                                onClick = {
                                                    onCategoryChange(category)
                                                    categoryExpanded = false
                                                },
                                                modifier = Modifier.background(Color.White)
                                            )
                                        }
                                    }
                                }
                            }
                        }

                        // 3. WORKING REQUIREMENT (Start Time)
                        item {
                            val isPreBooking = state.draftBookingType == "PRE_BOOKING"
                            LaunchedEffect(isPreBooking) {
                                if (isPreBooking && state.draftWorkingRequirementType == "IMMEDIATE") {
                                    onWorkingRequirementTypeChange("DYNAMIC_TIME")
                                }
                            }

                            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                Text(
                                    text = if (isPreBooking) "Working Start Time (Required for Pre-Booking)" else "Working Requirement (Start Time)",
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color.Black
                                )

                                val isImmediate = state.draftWorkingRequirementType == "IMMEDIATE" && !isPreBooking
                                val isDynamic = state.draftWorkingRequirementType == "DYNAMIC_TIME" || isPreBooking

                                if (!isPreBooking) {
                                    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                                        // Immediate Card
                                        Surface(
                                            modifier = Modifier
                                                .weight(1f)
                                                .clickable { onWorkingRequirementTypeChange("IMMEDIATE") },
                                            shape = RoundedCornerShape(12.dp),
                                            color = if (isImmediate) Color(0xFFEAF5D8) else Color.White,
                                            border = BorderStroke(
                                                width = if (isImmediate) 2.dp else 1.dp,
                                                color = if (isImmediate) ErnoGreen else Color(0xFFD0D0D0)
                                            )
                                        ) {
                                            Column(modifier = Modifier.padding(12.dp)) {
                                                Row(
                                                    verticalAlignment = Alignment.CenterVertically,
                                                    horizontalArrangement = Arrangement.SpaceBetween,
                                                    modifier = Modifier.fillMaxWidth()
                                                ) {
                                                    Text(
                                                        text = "Immediate",
                                                        fontSize = 14.sp,
                                                        fontWeight = FontWeight.Bold,
                                                        color = Color.Black
                                                    )
                                                    RadioButton(
                                                        selected = isImmediate,
                                                        onClick = { onWorkingRequirementTypeChange("IMMEDIATE") },
                                                        colors = RadioButtonDefaults.colors(selectedColor = ErnoGreen),
                                                        modifier = Modifier.size(20.dp)
                                                    )
                                                }
                                                Spacer(modifier = Modifier.height(2.dp))
                                                Text(
                                                    text = "Need worker as soon as possible.",
                                                    fontSize = 11.sp,
                                                    color = Color.Gray
                                                )
                                            }
                                        }

                                        // Select Time Card
                                        Surface(
                                            modifier = Modifier
                                                .weight(1f)
                                                .clickable { onWorkingRequirementTypeChange("DYNAMIC_TIME") },
                                            shape = RoundedCornerShape(12.dp),
                                            color = if (isDynamic) Color(0xFFEAF5D8) else Color.White,
                                            border = BorderStroke(
                                                width = if (isDynamic) 2.dp else 1.dp,
                                                color = if (isDynamic) ErnoGreen else Color(0xFFD0D0D0)
                                            )
                                        ) {
                                            Column(modifier = Modifier.padding(12.dp)) {
                                                Row(
                                                    verticalAlignment = Alignment.CenterVertically,
                                                    horizontalArrangement = Arrangement.SpaceBetween,
                                                    modifier = Modifier.fillMaxWidth()
                                                ) {
                                                    Text(
                                                        text = "Select Time",
                                                        fontSize = 14.sp,
                                                        fontWeight = FontWeight.Bold,
                                                        color = Color.Black
                                                    )
                                                    RadioButton(
                                                        selected = isDynamic,
                                                        onClick = { onWorkingRequirementTypeChange("DYNAMIC_TIME") },
                                                        colors = RadioButtonDefaults.colors(selectedColor = ErnoGreen),
                                                        modifier = Modifier.size(20.dp)
                                                    )
                                                }
                                                Spacer(modifier = Modifier.height(2.dp))
                                                Text(
                                                    text = "Choose exact start time.",
                                                    fontSize = 11.sp,
                                                    color = Color.Gray
                                                )
                                            }
                                        }
                                    }
                                }

                                // Time Picker Display & Trigger
                                if (isDynamic || isPreBooking) {
                                    Surface(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .clickable { timePickerDialog.show() },
                                        shape = RoundedCornerShape(10.dp),
                                        color = Color.White,
                                        border = BorderStroke(1.dp, ErnoGreen)
                                    ) {
                                        Row(
                                            modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp),
                                            verticalAlignment = Alignment.CenterVertically,
                                            horizontalArrangement = Arrangement.SpaceBetween
                                        ) {
                                            Row(verticalAlignment = Alignment.CenterVertically) {
                                                Icon(
                                                    imageVector = Icons.Default.AccessTime,
                                                    contentDescription = null,
                                                    tint = ErnoGreen,
                                                    modifier = Modifier.size(20.dp)
                                                )
                                                Spacer(modifier = Modifier.width(8.dp))
                                                Text(
                                                    text = if (state.draftScheduledTime.isNotBlank() && state.draftScheduledTime != "Immediate") {
                                                        "Start Time: ${state.draftScheduledTime}"
                                                    } else {
                                                        "Tap to Choose Start Time (e.g. 08:30 AM)"
                                                    },
                                                    fontSize = 13.sp,
                                                    fontWeight = FontWeight.Bold,
                                                    color = if (state.draftScheduledTime.isNotBlank() && state.draftScheduledTime != "Immediate") Color.Black else Color.Gray
                                                )
                                            }

                                            Surface(
                                                shape = RoundedCornerShape(6.dp),
                                                color = Color(0xFFEAF5D8)
                                            ) {
                                                Text(
                                                    text = "Time Picker",
                                                    fontSize = 11.sp,
                                                    fontWeight = FontWeight.Bold,
                                                    color = ErnoGreen,
                                                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                                                )
                                            }
                                        }
                                    }

                                    if (state.draftScheduledTime.isBlank() || state.draftScheduledTime == "Immediate") {
                                        Text(
                                            text = if (isPreBooking) "Pre-Bookings require selecting a specific start time using the time picker." else "Please select a start time using the time picker.",
                                            color = Color(0xFFD32F2F),
                                            fontSize = 11.sp,
                                            fontWeight = FontWeight.Medium
                                        )
                                    }
                                }
                            }
                        }

                        // 4. JOB DESCRIPTION
                        item {
                            Column {
                                Text(
                                    text = "Job Description",
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color.Black
                                )
                                Spacer(modifier = Modifier.height(4.dp))
                                OutlinedTextField(
                                    value = state.draftDescription,
                                    onValueChange = { if (it.length <= 250) onDescriptionChange(it) },
                                    placeholder = { Text("Describe work tasks, requirements, or duties...", color = Color.Gray) },
                                    textStyle = LocalTextStyle.current.copy(color = Color.Black, fontSize = 13.sp),
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .height(110.dp),
                                    shape = RoundedCornerShape(10.dp),
                                    colors = OutlinedTextFieldDefaults.colors(
                                        focusedTextColor = Color.Black,
                                        unfocusedTextColor = Color.Black,
                                        focusedBorderColor = ErnoGreen,
                                        unfocusedBorderColor = Color(0xFFE0E0E0),
                                        focusedContainerColor = Color.White,
                                        unfocusedContainerColor = Color.White
                                    )
                                )
                                Spacer(modifier = Modifier.height(2.dp))
                                Text(
                                    text = "${state.draftDescription.length}/250",
                                    fontSize = 10.sp,
                                    color = Color.Gray,
                                    modifier = Modifier.align(Alignment.End)
                                )
                            }
                        }
                    }

                    // STEP 2: SINGLE CHOICE DURATION SELECTION & CUSTOM DURATION/PRICE
                    if (currentStep == 2) {
                        item {
                            Column {
                                Text(
                                    text = "How much time do you need the worker for?",
                                    fontSize = 16.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color.Black
                                )
                                Text(
                                    text = "Select ONLY 1 duration option or set a custom time & price below:",
                                    fontSize = 12.sp,
                                    color = ErnoTextSecondary
                                )
                            }
                        }

                        // Single Choice RadioButton Cards (Supports both standard + custom options)
                        items(allDurationOptions) { option ->
                            val isSelected = state.draftPayStructure.firstOrNull()?.hours == option.hours
                            val currentPrice = if (isSelected) state.draftPayStructure.first().price else option.price

                            Surface(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable { onToggleDuration(option.hours, currentPrice) },
                                shape = RoundedCornerShape(14.dp),
                                color = Color.White,
                                border = BorderStroke(
                                    width = if (isSelected) 2.dp else 1.dp,
                                    color = if (isSelected) ErnoGreen else Color(0xFFE0E0E0)
                                )
                            ) {
                                Row(
                                    modifier = Modifier
                                        .padding(horizontal = 16.dp, vertical = 14.dp)
                                        .fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        RadioButton(
                                            selected = isSelected,
                                            onClick = { onToggleDuration(option.hours, currentPrice) },
                                            colors = RadioButtonDefaults.colors(selectedColor = ErnoGreen)
                                        )

                                        Spacer(modifier = Modifier.width(8.dp))

                                        Column {
                                            Text(
                                                text = "${option.hours} Hour${if (option.hours > 1) "s" else ""}" + if (option.hours == 8) " (Full Shift)" else "",
                                                fontSize = 15.sp,
                                                fontWeight = FontWeight.Bold,
                                                color = Color.Black
                                            )
                                            Text(
                                                text = "Pay Rate: ₹$currentPrice",
                                                fontSize = 12.sp,
                                                color = ErnoTextSecondary
                                            )
                                        }
                                    }

                                    if (isSelected) {
                                        Surface(
                                            shape = RoundedCornerShape(8.dp),
                                            color = Color(0xFFEAF5D8)
                                        ) {
                                            Row(
                                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
                                                verticalAlignment = Alignment.CenterVertically
                                            ) {
                                                Icon(
                                                    imageVector = Icons.Default.Check,
                                                    contentDescription = null,
                                                    tint = ErnoGreen,
                                                    modifier = Modifier.size(14.dp)
                                                )
                                                Spacer(modifier = Modifier.width(4.dp))
                                                Text(
                                                    text = "Selected",
                                                    fontSize = 12.sp,
                                                    fontWeight = FontWeight.Bold,
                                                    color = ErnoGreen
                                                )
                                            }
                                        }
                                    }
                                }
                            }
                        }

                        // Pricing duration options are approved and published by the backend.
                        item {
                            Surface(
                                modifier = Modifier.fillMaxWidth().clickable(onClick = onAddMoreDurationClick),
                                shape = RoundedCornerShape(12.dp),
                                color = Color.White,
                                border = BorderStroke(1.dp, ErnoGreen)
                            ) {
                                Text(
                                    text = "View approved price options",
                                    modifier = Modifier.fillMaxWidth().padding(vertical = 12.dp),
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = ErnoGreen,
                                    textAlign = androidx.compose.ui.text.style.TextAlign.Center
                                )
                            }
                        }
                    }

                    // STEP 3: BEGINNER-FRIENDLY LOCATION & MAP SELECTION WITH AUTO-SUGGEST
                    if (currentStep == 3) {
                        item {
                            Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                                Text(
                                    text = if (state.draftIsDelivery) "Where is the pickup & drop location?" else "Where is your shop located?",
                                    fontSize = 18.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color.Black
                                )
                                Text(
                                    text = "Tap the green button below or type to get automatic location suggestions.",
                                    fontSize = 13.sp,
                                    color = Color.Gray
                                )
                            }
                        }

                        if (state.draftIsDelivery) {
                            item {
                                SimpleBeginnerLocationInput(
                                    value = state.draftPickupLocation,
                                    onValueChange = onPickupLocationChange,
                                    label = "Pickup Store Address",
                                    placeholder = "Type store address for suggestions..."
                                )
                            }

                            item {
                                SimpleBeginnerLocationInput(
                                    value = state.draftDropLocation,
                                    onValueChange = onDropLocationChange,
                                    label = "Customer Drop Address",
                                    placeholder = "Type delivery address for suggestions..."
                                )
                            }
                        } else {
                            item {
                                SimpleBeginnerLocationInput(
                                    value = state.draftLocation,
                                    onValueChange = onLocationChange,
                                    label = "Shop / Work Address",
                                    placeholder = "Type shop address (e.g. Okhla, Noida)..."
                                )
                            }
                        }

                        item {
                            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                Text(
                                    text = "Map Preview (Leaflet API)",
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color.Black
                                )

                                WorkerLocationMapView(
                                    locationName = state.draftLocation.ifBlank { "Okhla Market Area" },
                                    distanceText = "Selected Location Pin",
                                    isDarkTheme = false
                                )
                            }
                        }
                    }
                }
            }
        }
    }

}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SimpleBeginnerLocationInput(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    placeholder: String
) {
    var expanded by remember { mutableStateOf(false) }

    val allLocations = listOf(
        "Okhla Market Store #12, Block B, New Delhi",
        "Okhla Industrial Area Phase 1, New Delhi",
        "Okhla Industrial Estate Phase 3, Delhi",
        "Okhla Phase 3 Metro Station Exit 2",
        "Okhla Main Market, Jamia Nagar, New Delhi",
        "Sector 18 Noida Market Area, UP",
        "Sector 15 Noida Metro Station, UP",
        "Sector 62 Noida IT Park, UP",
        "Connaught Place Central Market, New Delhi",
        "Lajpat Nagar Central Market, New Delhi",
        "Karol Bagh Wholesale Market, New Delhi",
        "Chandni Chowk Wholesale Store, Delhi",
        "Nehru Place Electronics Hub, Delhi",
        "Saket Select Citywalk Area, New Delhi",
        "South Extension Market Part 1, Delhi"
    )

    val suggestions = remember(value) {
        if (value.isBlank()) {
            emptyList()
        } else {
            allLocations.filter { it.contains(value, ignoreCase = true) }
        }
    }

    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(
            text = label,
            fontSize = 14.sp,
            fontWeight = FontWeight.Bold,
            color = Color.Black
        )

        // 1-Tap Big Friendly GPS Location Button
        Button(
            onClick = { onValueChange("Okhla Market Store #12, New Delhi") },
            modifier = Modifier
                .fillMaxWidth()
                .height(52.dp),
            colors = ButtonDefaults.buttonColors(containerColor = ErnoGreen),
            shape = RoundedCornerShape(12.dp)
        ) {
            Icon(
                imageVector = Icons.Default.MyLocation,
                contentDescription = null,
                tint = Color.White,
                modifier = Modifier.size(20.dp)
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = "📍 Tap Here to Use My Current Location",
                fontSize = 14.sp,
                fontWeight = FontWeight.Bold,
                color = Color.White
            )
        }

        // Popular Area One-Tap Cards
        Text(
            text = "Or tap a popular area below:",
            fontSize = 12.sp,
            fontWeight = FontWeight.SemiBold,
            color = Color.Gray
        )

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(6.dp)
        ) {
            val areas = listOf("Okhla Market", "Sector 18 Noida", "Lajpat Nagar", "Connaught Place")
            areas.forEach { area ->
                val isSelected = value.contains(area, ignoreCase = true)
                Surface(
                    onClick = { onValueChange("$area Store, New Delhi") },
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(10.dp),
                    color = if (isSelected) Color(0xFFEAF5D8) else Color.White,
                    border = BorderStroke(1.dp, if (isSelected) ErnoGreen else Color(0xFFD0D0D0))
                ) {
                    Box(
                        modifier = Modifier.padding(vertical = 10.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = area,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = if (isSelected) ErnoGreen else Color.Black
                        )
                    }
                }
            }
        }

        Spacer(modifier = Modifier.height(2.dp))

        // Simple Plain Text Box with Automatic Suggestion Dropdown
        ExposedDropdownMenuBox(
            expanded = expanded && suggestions.isNotEmpty(),
            onExpandedChange = { expanded = !expanded }
        ) {
            OutlinedTextField(
                value = value,
                onValueChange = {
                    onValueChange(it)
                    expanded = true
                },
                placeholder = { Text(placeholder, color = Color.Gray) },
                textStyle = LocalTextStyle.current.copy(color = Color.Black, fontSize = 14.sp),
                leadingIcon = {
                    Icon(
                        imageVector = Icons.Default.LocationOn,
                        contentDescription = null,
                        tint = ErnoGreen
                    )
                },
                modifier = Modifier
                    .fillMaxWidth()
                    .menuAnchor(),
                shape = RoundedCornerShape(12.dp),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedTextColor = Color.Black,
                    unfocusedTextColor = Color.Black,
                    focusedBorderColor = ErnoGreen,
                    unfocusedBorderColor = Color(0xFFD0D0D0),
                    focusedContainerColor = Color.White,
                    unfocusedContainerColor = Color.White
                ),
                singleLine = true
            )

            ExposedDropdownMenu(
                expanded = expanded && suggestions.isNotEmpty(),
                onDismissRequest = { expanded = false },
                modifier = Modifier.background(Color.White)
            ) {
                suggestions.forEach { suggestion ->
                    DropdownMenuItem(
                        text = {
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Icon(
                                    imageVector = Icons.Default.LocationOn,
                                    contentDescription = null,
                                    tint = ErnoGreen,
                                    modifier = Modifier.size(16.dp)
                                )
                                Spacer(modifier = Modifier.width(8.dp))
                                Text(
                                    text = suggestion,
                                    fontSize = 13.sp,
                                    color = Color.Black,
                                    fontWeight = FontWeight.Medium
                                )
                            }
                        },
                        onClick = {
                            onValueChange(suggestion)
                            expanded = false
                        },
                        modifier = Modifier.background(Color.White)
                    )
                }
            }
        }
    }
}

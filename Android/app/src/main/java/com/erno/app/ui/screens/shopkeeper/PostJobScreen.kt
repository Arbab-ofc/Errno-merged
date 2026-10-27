package com.erno.app.ui.screens.shopkeeper

import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.CalendarToday
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.MyLocation
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.erno.app.data.model.DurationPay
import com.erno.app.ui.components.WorkerLocationMapView
import com.erno.app.ui.theme.ErnoGreen
import com.erno.app.ui.theme.ErnoTextSecondary
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PostJobScreen(
    state: ShopkeeperState,
    onBackClick: () -> Unit,
    onTitleChange: (String) -> Unit,
    onCategoryChange: (String) -> Unit,
    onLocationChange: (String) -> Unit,
    onScheduledDateChange: (String) -> Unit = {},
    onPickupLocationChange: (String) -> Unit = {},
    onDropLocationChange: (String) -> Unit = {},
    onPackageTypeChange: (String) -> Unit = {},
    onDescriptionChange: (String) -> Unit,
    onRemoveDuration: (DurationPay) -> Unit,
    onToggleDuration: (hours: Int, price: Int) -> Unit = { _, _ -> },
    onAddMoreDurationClick: () -> Unit,
    onPreviewJobClick: () -> Unit
) {
    var currentStep by remember { mutableIntStateOf(1) } // Step 1: Details, Step 2: Time & Hours, Step 3: Location & Map
    var categoryExpanded by remember { mutableStateOf(false) }
    var showCustomDurationDialog by remember { mutableStateOf(false) }
    var customHoursInput by remember { mutableStateOf("5") }
    var customPayInput by remember { mutableStateOf("550") }

    val categories = listOf("Delivery Partner", "Shop Helper", "Counter Staff", "Store Assistant", "Packing Staff", "Delivery Boy", "Cashier")

    // Combined duration list containing standard options + any custom user-added duration option
    val allDurationOptions = remember(state.draftPayStructure) {
        val standard = listOf(
            DurationPay(1, 149),
            DurationPay(2, 249),
            DurationPay(3, 349),
            DurationPay(4, 449),
            DurationPay(6, 649),
            DurationPay(8, 849)
        )
        val customItems = state.draftPayStructure.filter { customItem ->
            standard.none { it.hours == customItem.hours }
        }
        (standard + customItems).sortedBy { it.hours }
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
                                1 -> "Basic Details & Calendar Schedule"
                                2 -> "Select Duration Needed"
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
                color = Color.White,
                shadowElevation = 8.dp
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(16.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    if (currentStep > 1) {
                        OutlinedButton(
                            onClick = { currentStep-- },
                            modifier = Modifier
                                .weight(1f)
                                .height(52.dp),
                            shape = RoundedCornerShape(12.dp),
                            border = BorderStroke(1.dp, Color(0xFFD0D0D0))
                        ) {
                            Text(
                                text = "← Back",
                                fontSize = 15.sp,
                                color = Color.Black,
                                fontWeight = FontWeight.SemiBold
                            )
                        }
                    }

                    Button(
                        onClick = {
                            if (currentStep < 3) {
                                currentStep++
                            } else {
                                onPreviewJobClick()
                            }
                        },
                        modifier = Modifier
                            .weight(1f)
                            .height(52.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = ErnoGreen),
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Text(
                            text = when (currentStep) {
                                1 -> "Next: Select Duration →"
                                2 -> "Next: Location →"
                                else -> "Preview & Post →"
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
                    .padding(horizontal = 20.dp, vertical = 12.dp),
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
                            modifier = Modifier.padding(vertical = 8.dp),
                            contentAlignment = Alignment.Center
                        ) {
                            Text(
                                text = title,
                                fontSize = 12.sp,
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
                    .padding(horizontal = 20.dp, vertical = 12.dp),
                contentAlignment = Alignment.TopCenter
            ) {
                LazyColumn(
                    modifier = Modifier
                        .fillMaxSize()
                        .widthIn(max = 800.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    // STEP 1: JOB TITLE, CALENDAR DATE PRE-BOOKING & START TIME PICKER
                    if (currentStep == 1) {
                        item {
                            Text(
                                text = "Basic Information & Calendar Booking",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.Black
                            )
                        }

                        // Category Dropdown
                        item {
                            Column {
                                Text(
                                    text = "Job Category",
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Medium,
                                    color = Color.Black
                                )
                                Spacer(modifier = Modifier.height(6.dp))
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
                                        textStyle = LocalTextStyle.current.copy(color = Color.Black),
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
                                                text = { Text(category, color = Color.Black, fontWeight = FontWeight.Medium) },
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

                        // Interactive Calendar Date & Time Pre-Booking Selection
                        item {
                            var showDatePicker by remember { mutableStateOf(false) }
                            var selectedTime by remember { mutableStateOf("01:00 PM") }
                            var selectedDateFormatted by remember { mutableStateOf("12 Sep 2026") }
                            var timeExpanded by remember { mutableStateOf(false) }

                            val timeOptions = listOf(
                                "09:00 AM",
                                "10:00 AM",
                                "11:00 AM",
                                "12:00 PM",
                                "01:00 PM",
                                "02:00 PM",
                                "03:00 PM",
                                "04:00 PM",
                                "05:00 PM",
                                "06:00 PM",
                                "07:00 PM",
                                "08:00 PM"
                            )

                            // DatePicker State with 6-Day Future Limit Constraint
                            val datePickerState = rememberDatePickerState(
                                initialSelectedDateMillis = System.currentTimeMillis(),
                                selectableDates = object : SelectableDates {
                                    override fun isSelectableDate(utcTimeMillis: Long): Boolean {
                                        val today = System.currentTimeMillis()
                                        val maxMillis = today + (6 * 24 * 60 * 60 * 1000L) // 6 Days Max Limit
                                        return utcTimeMillis >= (today - (24 * 60 * 60 * 1000L)) && utcTimeMillis <= maxMillis
                                    }
                                }
                            )

                            if (showDatePicker) {
                                DatePickerDialog(
                                    onDismissRequest = { showDatePicker = false },
                                    confirmButton = {
                                        TextButton(onClick = {
                                            datePickerState.selectedDateMillis?.let { millis ->
                                                val sdf = SimpleDateFormat("dd MMM yyyy", Locale.getDefault())
                                                selectedDateFormatted = sdf.format(Date(millis))
                                                onScheduledDateChange("$selectedDateFormatted at $selectedTime")
                                            }
                                            showDatePicker = false
                                        }) {
                                            Text("Confirm Date", color = ErnoGreen, fontWeight = FontWeight.Bold)
                                        }
                                    },
                                    dismissButton = {
                                        TextButton(onClick = { showDatePicker = false }) {
                                            Text("Cancel", color = Color.Gray)
                                        }
                                    }
                                ) {
                                    DatePicker(state = datePickerState)
                                }
                            }

                            Column(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .background(Color.White, RoundedCornerShape(14.dp))
                                    .border(1.dp, Color(0xFFE0E0E0), RoundedCornerShape(14.dp))
                                    .padding(16.dp)
                            ) {
                                Text(
                                    text = "Select Schedule Date & Time (Calendar)",
                                    fontSize = 15.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color.Black
                                )
                                Text(
                                    text = "Current Month Calendar • Maximum 6-Day Pre-Booking Limit",
                                    fontSize = 11.sp,
                                    color = Color.Gray
                                )

                                Spacer(modifier = Modifier.height(14.dp))

                                // Date Selection Input Field
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                                ) {
                                    OutlinedTextField(
                                        value = selectedDateFormatted,
                                        onValueChange = {},
                                        readOnly = true,
                                        label = { Text("Work Date (Calendar)", fontSize = 12.sp, color = Color.Gray) },
                                        leadingIcon = {
                                            Icon(
                                                imageVector = Icons.Default.CalendarToday,
                                                contentDescription = null,
                                                tint = ErnoGreen,
                                                modifier = Modifier.size(18.dp)
                                            )
                                        },
                                        trailingIcon = {
                                            TextButton(onClick = { showDatePicker = true }) {
                                                Text("Change", color = ErnoGreen, fontWeight = FontWeight.Bold, fontSize = 12.sp)
                                            }
                                        },
                                        modifier = Modifier
                                            .weight(1.2f)
                                            .clickable { showDatePicker = true },
                                        shape = RoundedCornerShape(10.dp),
                                        colors = OutlinedTextFieldDefaults.colors(
                                            focusedTextColor = Color.Black,
                                            unfocusedTextColor = Color.Black,
                                            focusedBorderColor = ErnoGreen,
                                            unfocusedBorderColor = Color(0xFFD0D0D0)
                                        ),
                                        singleLine = true
                                    )

                                    ExposedDropdownMenuBox(
                                        expanded = timeExpanded,
                                        onExpandedChange = { timeExpanded = !timeExpanded },
                                        modifier = Modifier.weight(1f)
                                    ) {
                                        OutlinedTextField(
                                            value = selectedTime,
                                            onValueChange = {},
                                            readOnly = true,
                                            label = { Text("Start Time", fontSize = 12.sp, color = Color.Gray) },
                                            trailingIcon = {
                                                Icon(
                                                    imageVector = Icons.Default.KeyboardArrowDown,
                                                    contentDescription = null,
                                                    tint = Color.Black
                                                )
                                            },
                                            modifier = Modifier
                                                .fillMaxWidth()
                                                .menuAnchor(),
                                            shape = RoundedCornerShape(10.dp),
                                            colors = OutlinedTextFieldDefaults.colors(
                                                focusedTextColor = Color.Black,
                                                unfocusedTextColor = Color.Black,
                                                focusedBorderColor = ErnoGreen,
                                                unfocusedBorderColor = Color(0xFFD0D0D0)
                                            ),
                                            singleLine = true
                                        )

                                        ExposedDropdownMenu(
                                            expanded = timeExpanded,
                                            onDismissRequest = { timeExpanded = false },
                                            modifier = Modifier.background(Color.White)
                                        ) {
                                            timeOptions.forEach { timeSlot ->
                                                DropdownMenuItem(
                                                    text = { Text(timeSlot, color = Color.Black, fontWeight = FontWeight.Medium) },
                                                    onClick = {
                                                        selectedTime = timeSlot
                                                        timeExpanded = false
                                                        onScheduledDateChange("$selectedDateFormatted at $selectedTime")
                                                    },
                                                    modifier = Modifier.background(Color.White)
                                                )
                                            }
                                        }
                                    }
                                }

                                Spacer(modifier = Modifier.height(12.dp))

                                Surface(
                                    shape = RoundedCornerShape(8.dp),
                                    color = Color(0xFFEAF5D8)
                                ) {
                                    Row(
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .padding(horizontal = 12.dp, vertical = 8.dp),
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Icon(
                                            imageVector = Icons.Default.Schedule,
                                            contentDescription = null,
                                            tint = ErnoGreen,
                                            modifier = Modifier.size(16.dp)
                                        )
                                        Spacer(modifier = Modifier.width(6.dp))
                                        Text(
                                            text = "Scheduled Work: $selectedDateFormatted at $selectedTime",
                                            fontSize = 12.sp,
                                            fontWeight = FontWeight.Bold,
                                            color = ErnoGreen
                                        )
                                    }
                                }
                            }
                        }

                        // Description Input
                        item {
                            Column {
                                Text(
                                    text = "Job Description & Requirements",
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Medium,
                                    color = Color.Black
                                )
                                Spacer(modifier = Modifier.height(6.dp))
                                OutlinedTextField(
                                    value = state.draftDescription,
                                    onValueChange = { if (it.length <= 250) onDescriptionChange(it) },
                                    placeholder = { Text("Enter work details, tasks, or requirements...", color = Color.Gray) },
                                    textStyle = LocalTextStyle.current.copy(color = Color.Black),
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
                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = "${state.draftDescription.length}/250",
                                    fontSize = 11.sp,
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

                        // Add Custom Hour Button (Opens Custom Duration & Price Dialog)
                        item {
                            Surface(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable { showCustomDurationDialog = true },
                                shape = RoundedCornerShape(12.dp),
                                color = Color.White,
                                border = BorderStroke(1.dp, ErnoGreen)
                            ) {
                                Row(
                                    modifier = Modifier.padding(vertical = 12.dp),
                                    horizontalArrangement = Arrangement.Center,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.Add,
                                        contentDescription = null,
                                        tint = ErnoGreen,
                                        modifier = Modifier.size(20.dp)
                                    )
                                    Spacer(modifier = Modifier.width(6.dp))
                                    Text(
                                        text = "+ Set Custom Duration & Price",
                                        fontSize = 14.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = ErnoGreen
                                    )
                                }
                            }
                        }
                    }

                    // STEP 3: LOCATION & MAP PIN WITH AUTOCOMPLETE RECOMMENDATIONS
                    if (currentStep == 3) {
                        item {
                            Text(
                                text = if (state.draftIsDelivery) "Delivery Route Locations" else "Shop Location & Map Pin",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.Black
                            )
                        }

                        if (state.draftIsDelivery) {
                            // Delivery Job: ONLY 2 address fields (Pickup Location & Drop Location)
                            item {
                                LocationAutocompleteTextField(
                                    value = state.draftPickupLocation,
                                    onValueChange = onPickupLocationChange,
                                    label = "Pickup Location",
                                    placeholder = "Pickup Store Address",
                                    leadingIcon = {
                                        Icon(
                                            imageVector = Icons.Default.LocationOn,
                                            contentDescription = null,
                                            tint = Color.Gray
                                        )
                                    },
                                    modifier = Modifier.fillMaxWidth()
                                )
                            }

                            item {
                                LocationAutocompleteTextField(
                                    value = state.draftDropLocation,
                                    onValueChange = onDropLocationChange,
                                    label = "Customer Drop Location",
                                    placeholder = "Delivery Address",
                                    leadingIcon = {
                                        Icon(
                                            imageVector = Icons.Default.LocationOn,
                                            contentDescription = null,
                                            tint = Color.Gray
                                        )
                                    },
                                    modifier = Modifier.fillMaxWidth()
                                )
                            }
                        } else {
                            // Non-Delivery Job: ONLY 1 address field (Shop / Work Address)
                            item {
                                LocationAutocompleteTextField(
                                    value = state.draftLocation,
                                    onValueChange = onLocationChange,
                                    label = "Shop / Work Address",
                                    placeholder = "e.g. Shop #12, Okhla Market Area",
                                    leadingIcon = {
                                        Icon(
                                            imageVector = Icons.Default.LocationOn,
                                            contentDescription = null,
                                            tint = Color.Gray
                                        )
                                    },
                                    modifier = Modifier.fillMaxWidth()
                                )
                            }
                        }

                        item {
                            Column {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Text(
                                        text = "Interactive Location Map Pin:",
                                        fontSize = 13.sp,
                                        fontWeight = FontWeight.Bold,
                                        color = Color.Black
                                    )
                                    Text(
                                        text = "🎯 Tap map to preview",
                                        fontSize = 11.sp,
                                        color = ErnoGreen,
                                        fontWeight = FontWeight.SemiBold
                                    )
                                }
                                Spacer(modifier = Modifier.height(6.dp))

                                // Quick Map Pin Presets
                                LazyRow(
                                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                                    modifier = Modifier.padding(bottom = 8.dp)
                                ) {
                                    val mapPresets = listOf(
                                        "🏬 Shop Main Gate, Okhla",
                                        "📍 Store Delivery Bay, Block B",
                                        "🚇 Okhla Metro Exit 2",
                                        "🏢 Central Market Hub"
                                    )
                                    items(mapPresets) { preset ->
                                        Surface(
                                            onClick = {
                                                if (state.draftIsDelivery) {
                                                    onPickupLocationChange(preset)
                                                } else {
                                                    onLocationChange(preset)
                                                }
                                            },
                                            shape = RoundedCornerShape(20.dp),
                                            color = Color(0xFFEAF5D8),
                                            border = BorderStroke(1.dp, ErnoGreen.copy(alpha = 0.6f))
                                        ) {
                                            Text(
                                                text = preset,
                                                fontSize = 11.sp,
                                                fontWeight = FontWeight.Bold,
                                                color = ErnoGreen,
                                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                                            )
                                        }
                                    }
                                }

                                WorkerLocationMapView(
                                    locationName = state.draftLocation.ifBlank { "Okhla Market Area" },
                                    distanceText = "Shop Location Map Pin",
                                    isDarkTheme = false
                                )
                            }
                        }
                    }
                }
            }
        }
    }

    // CUSTOM DURATION & PRICE DIALOG
    if (showCustomDurationDialog) {
        AlertDialog(
            onDismissRequest = { showCustomDurationDialog = false },
            containerColor = Color.White,
            titleContentColor = Color.Black,
            textContentColor = Color.Black,
            title = {
                Text(
                    text = "Set Custom Duration & Pay",
                    fontWeight = FontWeight.Bold,
                    fontSize = 18.sp,
                    color = Color.Black
                )
            },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    Text(
                        text = "Enter custom shift time duration (hours) and total pay rate for the worker:",
                        fontSize = 12.sp,
                        color = Color.Gray
                    )

                    OutlinedTextField(
                        value = customHoursInput,
                        onValueChange = { if (it.all { char -> char.isDigit() }) customHoursInput = it },
                        label = { Text("Duration Hours (e.g. 5 or 10)", color = Color.Gray) },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        textStyle = LocalTextStyle.current.copy(color = Color.Black, fontWeight = FontWeight.Bold),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedTextColor = Color.Black,
                            unfocusedTextColor = Color.Black,
                            focusedBorderColor = ErnoGreen,
                            unfocusedBorderColor = Color(0xFFD0D0D0)
                        ),
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(10.dp)
                    )

                    OutlinedTextField(
                        value = customPayInput,
                        onValueChange = { if (it.all { char -> char.isDigit() }) customPayInput = it },
                        label = { Text("Pay Rate Amount (₹)", color = Color.Gray) },
                        prefix = { Text("₹ ", color = Color.Black, fontWeight = FontWeight.Bold) },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        textStyle = LocalTextStyle.current.copy(color = Color.Black, fontWeight = FontWeight.Bold),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedTextColor = Color.Black,
                            unfocusedTextColor = Color.Black,
                            focusedBorderColor = ErnoGreen,
                            unfocusedBorderColor = Color(0xFFD0D0D0)
                        ),
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(10.dp)
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val hours = customHoursInput.toIntOrNull() ?: 5
                        val price = customPayInput.toIntOrNull() ?: 550
                        onToggleDuration(hours, price)
                        showCustomDurationDialog = false
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = ErnoGreen),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text("Set Duration Option", color = Color.White, fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { showCustomDurationDialog = false }) {
                    Text("Cancel", color = Color.Gray)
                }
            }
        )
    }
}

// LOCATION AUTOCOMPLETE TEXT FIELD WITH REAL-TIME RECOMMENDATION DROPDOWN
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun LocationAutocompleteTextField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    placeholder: String,
    leadingIcon: @Composable (() -> Unit)? = null,
    modifier: Modifier = Modifier
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
        if (value.isBlank() || value.length < 2) {
            emptyList()
        } else {
            allLocations.filter { it.contains(value, ignoreCase = true) }
        }
    }

    LaunchedEffect(suggestions) {
        expanded = suggestions.isNotEmpty()
    }

    Column(modifier = modifier) {
        Text(
            text = label,
            fontSize = 13.sp,
            fontWeight = FontWeight.Medium,
            color = Color.Black
        )
        Spacer(modifier = Modifier.height(6.dp))

        ExposedDropdownMenuBox(
            expanded = expanded && suggestions.isNotEmpty(),
            onExpandedChange = { expanded = !expanded }
        ) {
            OutlinedTextField(
                value = value,
                onValueChange = {
                    onValueChange(it)
                    expanded = it.length >= 2
                },
                placeholder = { Text(placeholder, color = Color.Gray) },
                textStyle = LocalTextStyle.current.copy(color = Color.Black),
                leadingIcon = leadingIcon,
                trailingIcon = {
                    if (value.isNotEmpty()) {
                        IconButton(onClick = { onValueChange("") }) {
                            Icon(Icons.Default.Close, contentDescription = "Clear", tint = Color.Gray, modifier = Modifier.size(16.dp))
                        }
                    }
                },
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
                ),
                singleLine = true
            )

            ExposedDropdownMenu(
                expanded = expanded && suggestions.isNotEmpty(),
                onDismissRequest = { expanded = false },
                modifier = Modifier
                    .background(Color.White)
                    .widthIn(max = 500.dp)
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

        // 1-TAP GPS LOCATION DETECT BUTTON & POPULAR NEARBY CHIPS
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 6.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Surface(
                onClick = { onValueChange("Okhla Market Store #12, Block B, New Delhi") },
                shape = RoundedCornerShape(8.dp),
                color = Color(0xFFEAF5D8),
                border = BorderStroke(1.dp, ErnoGreen.copy(alpha = 0.5f))
            ) {
                Row(
                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(
                        imageVector = Icons.Default.MyLocation,
                        contentDescription = null,
                        tint = ErnoGreen,
                        modifier = Modifier.size(14.dp)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = "📍 Use Current GPS Location",
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        color = ErnoGreen
                    )
                }
            }

            Text(
                text = "Type or select below",
                fontSize = 10.sp,
                color = Color.Gray
            )
        }

        // QUICK POPULAR CHIPS
        LazyRow(
            modifier = Modifier
                .fillMaxWidth()
                .padding(top = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            val quickChips = listOf(
                "Okhla Market #12",
                "Sector 18 Noida",
                "Nehru Place Hub",
                "Connaught Place",
                "Lajpat Nagar Market"
            )
            items(quickChips) { chip ->
                Surface(
                    onClick = { onValueChange("$chip, Delhi NCR") },
                    shape = RoundedCornerShape(16.dp),
                    color = Color(0xFFF8FAFC),
                    border = BorderStroke(1.dp, Color(0xFFCBD5E1))
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 5.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.Default.LocationOn,
                            contentDescription = null,
                            tint = ErnoGreen,
                            modifier = Modifier.size(12.dp)
                        )
                        Spacer(modifier = Modifier.width(4.dp))
                        Text(
                            text = chip,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Medium,
                            color = Color(0xFF334155)
                        )
                    }
                }
            }
        }
    }
}

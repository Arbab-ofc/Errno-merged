package com.erno.app.ui.screens.shopkeeper

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.Verified
import androidx.compose.material3.*
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.runtime.*
import com.erno.app.data.repository.ErrnoMobileApi
import kotlinx.coroutines.launch
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.graphics.ColorMatrix
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.erno.app.ui.components.ErnoLogo
import com.erno.app.ui.components.ShopkeeperBottomNavigation
import com.erno.app.ui.components.ShopkeeperTab
import com.erno.app.ui.theme.ErnoGreen
import com.erno.app.ui.theme.ErnoTextSecondary

data class ApplicationItem(
    val id: String,
    val jobId: String,
    val workerName: String,
    val jobTitle: String,
    val experience: String,
    val distance: String,
    val rating: String,
    val totalShiftsCompleted: Int = 0,
    val pastReviews: List<String> = emptyList(),
    var status: String // "Pending", "Accepted", "Declined"
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ShopkeeperApplicationsScreen(
    onBackClick: () -> Unit,
    onNavigateTab: (ShopkeeperTab) -> Unit
) {
    var selectedTabIndex by remember { mutableIntStateOf(0) } // 0: All, 1: Pending, 2: Accepted
    var selectedWorkerForReview by remember { mutableStateOf<ApplicationItem?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    // Starts empty (00) initially for new logins
    var applicationsList by remember { mutableStateOf(emptyList<ApplicationItem>()) }
    suspend fun loadApplications() {
        isLoading = true; errorMessage = null
        try {
            applicationsList = ErrnoMobileApi.ownerApplications().map { row ->
                ApplicationItem(id = row.getString("id"), jobId = row.getString("job_id"),
                    workerName = row.optString("worker_name").ifBlank { "Worker" }, jobTitle = row.getString("job_title"),
                    experience = "", distance = "", rating = "—",
                    status = when (row.optString("status")) { "accepted" -> "Accepted"; "rejected" -> "Declined"; else -> "Pending" })
            }
        } catch (error: Exception) { errorMessage = error.localizedMessage ?: "Unable to load applications." }
        finally { isLoading = false }
    }
    LaunchedEffect(Unit) { loadApplications() }

    val pendingApps = applicationsList.filter { it.status == "Pending" }
    val acceptedApps = applicationsList.filter { it.status == "Accepted" }

    val filteredList = when (selectedTabIndex) {
        0 -> applicationsList
        1 -> pendingApps
        else -> acceptedApps
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "Worker Applications",
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
            ShopkeeperBottomNavigation(
                selectedTab = ShopkeeperTab.APPLICATIONS,
                onTabSelected = onNavigateTab
            )
        },
        containerColor = Color(0xFFF9FAFB)
    ) { paddingValues ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
        ) {
            // Tab Row displaying 00 for initial counts
            TabRow(
                selectedTabIndex = selectedTabIndex,
                containerColor = Color.White,
                contentColor = ErnoGreen,
                indicator = { tabPositions ->
                    TabRowDefaults.SecondaryIndicator(
                        Modifier.tabIndicatorOffset(tabPositions[selectedTabIndex]),
                        color = ErnoGreen
                    )
                }
            ) {
                Tab(
                    selected = selectedTabIndex == 0,
                    onClick = { selectedTabIndex = 0 },
                    text = {
                        Text(
                            text = "All (${applicationsList.size})",
                            fontSize = 14.sp,
                            fontWeight = if (selectedTabIndex == 0) FontWeight.Bold else FontWeight.Medium,
                            color = if (selectedTabIndex == 0) ErnoGreen else Color.Gray
                        )
                    }
                )
                Tab(
                    selected = selectedTabIndex == 1,
                    onClick = { selectedTabIndex = 1 },
                    text = {
                        Text(
                            text = "Pending (${pendingApps.size})",
                            fontSize = 14.sp,
                            fontWeight = if (selectedTabIndex == 1) FontWeight.Bold else FontWeight.Medium,
                            color = if (selectedTabIndex == 1) ErnoGreen else Color.Gray
                        )
                    }
                )
                Tab(
                    selected = selectedTabIndex == 2,
                    onClick = { selectedTabIndex = 2 },
                    text = {
                        Text(
                            text = "Accepted (${acceptedApps.size})",
                            fontSize = 14.sp,
                            fontWeight = if (selectedTabIndex == 2) FontWeight.Bold else FontWeight.Medium,
                            color = if (selectedTabIndex == 2) ErnoGreen else Color.Gray
                        )
                    }
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            if (isLoading) {
                CircularProgressIndicator(modifier = Modifier.align(Alignment.CenterHorizontally), color = ErnoGreen)
            } else if (errorMessage != null) {
                Column(Modifier.fillMaxSize(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                    Text(errorMessage.orEmpty(), color = Color.DarkGray)
                    TextButton(onClick = { scope.launch { loadApplications() } }) { Text("Retry", color = ErnoGreen) }
                }
            } else if (filteredList.isEmpty()) {
                val monochromeMatrix = remember { ColorMatrix().apply { setToSaturation(0f) } }

                Box(
                    modifier = Modifier.fillMaxSize().padding(horizontal = 24.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Surface(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(16.dp),
                        color = Color.White,
                        border = BorderStroke(1.dp, Color(0xFFE0E0E0))
                    ) {
                        Column(
                            modifier = Modifier.padding(28.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            ErnoLogo(
                                modifier = Modifier.height(64.dp).graphicsLayer { alpha = 0.5f },
                                colorFilter = ColorFilter.colorMatrix(monochromeMatrix)
                            )
                            Spacer(modifier = Modifier.height(12.dp))
                            Text(
                                text = "No Applications Received Yet",
                                fontSize = 16.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.Black
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = "When workers apply for your posted jobs, their applications will appear here.",
                                fontSize = 12.sp,
                                color = Color.Gray,
                                textAlign = TextAlign.Center
                            )
                        }
                    }
                }
            } else {
                LazyColumn(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 20.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    items(filteredList) { app ->
                        ApplicationCardItem(
                            application = app,
                            onViewReviews = { selectedWorkerForReview = app },
                            onAccept = {
                                scope.launch {
                                    try {
                                        ErrnoMobileApi.decideApplication(app.jobId, app.id, "accepted")
                                        applicationsList = applicationsList.map { if (it.id == app.id) it.copy(status = "Accepted") else it }
                                    } catch (error: Exception) { errorMessage = error.localizedMessage ?: "Unable to accept application." }
                                }
                            },
                            onDecline = {
                                scope.launch {
                                    try {
                                        ErrnoMobileApi.decideApplication(app.jobId, app.id, "rejected")
                                        applicationsList = applicationsList.map { if (it.id == app.id) it.copy(status = "Declined") else it }
                                    } catch (error: Exception) { errorMessage = error.localizedMessage ?: "Unable to decline application." }
                                }
                            }
                        )
                    }
                    item {
                        Spacer(modifier = Modifier.height(16.dp))
                    }
                }
            }
        }
    }

    // WORKER RATINGS & PAST REVIEWS DIALOG (Right where shopkeeper accepts/declines)
    selectedWorkerForReview?.let { app ->
        AlertDialog(
            onDismissRequest = { selectedWorkerForReview = null },
            containerColor = Color.White,
            titleContentColor = Color.Black,
            textContentColor = Color.Black,
            title = {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.SpaceBetween,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column {
                        Text(
                            text = app.workerName,
                            fontSize = 18.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.Black
                        )
                        Text(
                            text = "Applied for: ${app.jobTitle}",
                            fontSize = 12.sp,
                            color = ErnoTextSecondary
                        )
                    }

                    Surface(
                        shape = RoundedCornerShape(8.dp),
                        color = Color(0xFFFFF8E1)
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                imageVector = Icons.Default.Star,
                                contentDescription = null,
                                tint = Color(0xFFFFB300),
                                modifier = Modifier.size(14.dp)
                            )
                            Spacer(modifier = Modifier.width(2.dp))
                            Text(
                                text = "${app.rating} ★",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.Black
                            )
                        }
                    }
                }
            },
            text = {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    // DigiLocker Verified Badge & Experience Stats
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = Color(0xFFE8F5E9)
                        ) {
                            Row(
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Verified,
                                    contentDescription = null,
                                    tint = Color(0xFF2E7D32),
                                    modifier = Modifier.size(12.dp)
                                )
                                Spacer(modifier = Modifier.width(4.dp))
                                Text(
                                    text = "Aadhaar Verified",
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF2E7D32)
                                )
                            }
                        }

                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = Color(0xFFF5F5F5)
                        ) {
                            Text(
                                text = "${app.totalShiftsCompleted} Shifts Completed",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Medium,
                                color = Color.DarkGray,
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                            )
                        }
                    }

                    HorizontalDivider(color = Color(0xFFF0F0F0))

                    Text(
                        text = "Past Shopkeeper Reviews & Ratings:",
                        fontSize = 13.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.Black
                    )

                    app.pastReviews.forEach { reviewText ->
                        Surface(
                            shape = RoundedCornerShape(10.dp),
                            color = Color(0xFFF8F9FA),
                            border = BorderStroke(1.dp, Color(0xFFE0E0E0)),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Row(
                                modifier = Modifier.padding(10.dp),
                                verticalAlignment = Alignment.Top
                            ) {
                                Text(
                                    text = "💬 ",
                                    fontSize = 12.sp
                                )
                                Text(
                                    text = "\"$reviewText\"",
                                    fontSize = 12.sp,
                                    color = Color.DarkGray,
                                    lineHeight = 16.sp
                                )
                            }
                        }
                    }
                }
            },
            confirmButton = {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedButton(
                        onClick = {
                            applicationsList = applicationsList.filter { it.id != app.id }
                            selectedWorkerForReview = null
                        },
                        modifier = Modifier.weight(1f),
                        border = BorderStroke(1.dp, Color.Gray)
                    ) {
                        Text("Decline", color = Color.Gray, fontSize = 13.sp)
                    }

                    Button(
                        onClick = {
                            applicationsList = applicationsList.map {
                                if (it.id == app.id) it.copy(status = "Accepted") else it
                            }
                            selectedWorkerForReview = null
                        },
                        modifier = Modifier.weight(1f),
                        colors = ButtonDefaults.buttonColors(containerColor = ErnoGreen)
                    ) {
                        Text("Accept Worker", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 13.sp)
                    }
                }
            }
        )
    }
}

@Composable
fun ApplicationCardItem(
    application: ApplicationItem,
    onViewReviews: () -> Unit,
    onAccept: () -> Unit,
    onDecline: () -> Unit
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        color = Color.White,
        shadowElevation = 1.dp
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.clickable { onViewReviews() }
                ) {
                    Box(
                        modifier = Modifier
                            .size(44.dp)
                            .background(Color(0xFFF1F8E9), CircleShape),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.Person,
                            contentDescription = null,
                            tint = ErnoGreen,
                            modifier = Modifier.size(24.dp)
                        )
                    }

                    Spacer(modifier = Modifier.width(12.dp))

                    Column {
                        Text(
                            text = application.workerName,
                            fontSize = 16.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.Black
                        )
                        Text(
                            text = "Applied for: ${application.jobTitle}",
                            fontSize = 12.sp,
                            color = ErnoTextSecondary
                        )
                    }
                }

                if (application.status == "Accepted") {
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = Color(0xFFE8F5E9)
                    ) {
                        Row(
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Icon(
                                imageVector = Icons.Default.Check,
                                contentDescription = null,
                                tint = Color(0xFF2E7D32),
                                modifier = Modifier.size(12.dp)
                            )
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(
                                text = "Accepted",
                                fontSize = 11.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF2E7D32)
                            )
                        }
                    }
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { onViewReviews() },
                horizontalArrangement = Arrangement.spacedBy(16.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = application.experience,
                    fontSize = 12.sp,
                    color = Color.Gray
                )
                Text(
                    text = "•",
                    fontSize = 12.sp,
                    color = Color.Gray
                )
                Text(
                    text = application.distance,
                    fontSize = 12.sp,
                    color = Color.Gray
                )
                Text(
                    text = "•",
                    fontSize = 12.sp,
                    color = Color.Gray
                )
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = Color(0xFFFFF8E1),
                    modifier = Modifier.clickable { onViewReviews() }
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Icon(
                            imageVector = Icons.Default.Star,
                            contentDescription = null,
                            tint = Color(0xFFFFB300),
                            modifier = Modifier.size(14.dp)
                        )
                        Spacer(modifier = Modifier.width(2.dp))
                        Text(
                            text = "${application.rating} ★ (Reviews)",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.Black
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            if (application.status == "Pending") {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    OutlinedButton(
                        onClick = onDecline,
                        modifier = Modifier
                            .weight(1f)
                            .height(44.dp),
                        shape = RoundedCornerShape(10.dp),
                        border = BorderStroke(1.dp, Color.LightGray)
                    ) {
                        Text(
                            text = "Decline",
                            fontSize = 14.sp,
                            color = Color.Gray
                        )
                    }

                    Button(
                        onClick = onAccept,
                        modifier = Modifier
                            .weight(1f)
                            .height(44.dp),
                        colors = ButtonDefaults.buttonColors(containerColor = ErnoGreen),
                        shape = RoundedCornerShape(10.dp)
                    ) {
                        Text(
                            text = "Accept Worker",
                            fontSize = 14.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        )
                    }
                }
            } else {
                Button(
                    onClick = { },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(44.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF0E1726)),
                    shape = RoundedCornerShape(10.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Phone,
                        contentDescription = null,
                        tint = Color.White,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Call Worker",
                        fontSize = 14.sp,
                        color = Color.White
                    )
                }
            }
        }
    }
}

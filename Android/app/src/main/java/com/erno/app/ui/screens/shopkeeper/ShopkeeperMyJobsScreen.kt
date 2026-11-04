package com.erno.app.ui.screens.shopkeeper

import android.content.Intent
import android.net.Uri
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
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.Verified
import androidx.compose.material3.*
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.foundation.layout.heightIn
import androidx.compose.material3.Slider
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.ui.unit.IntSize
import com.erno.app.data.model.MapCoordinate
import com.erno.app.data.model.NearbyWorker
import com.erno.app.data.model.ApproximateRoute
import com.erno.app.data.repository.ErrnoMobileApi
import com.erno.app.ui.components.WorkerLocationMapView
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.isActive
import org.json.JSONObject
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString
import java.util.concurrent.atomic.AtomicLong
import java.util.concurrent.atomic.AtomicBoolean
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.erno.app.data.model.JobPost
import com.erno.app.ui.components.RatingDialog
import com.erno.app.ui.components.ShopkeeperBottomNavigation
import com.erno.app.ui.components.ShopkeeperTab
import com.erno.app.ui.theme.ErnoGreen

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ShopkeeperMyJobsScreen(
    state: ShopkeeperState,
    onRefresh: () -> Unit,
    onBackClick: () -> Unit,
    onNavigateTab: (ShopkeeperTab) -> Unit,
    onRateWorkerClick: (jobId: String, rating: Float, comment: String) -> Unit = { _, _, _ -> },
    onJobLifecycleAction: (jobId: String, action: String) -> Unit = { _, _ -> },
    onPayJob: (jobId: String) -> Unit = {}
) {
    var selectedTabIndex by remember { mutableIntStateOf(1) } // 0: All, 1: Active, 2: Completed
    var ratingJob by remember { mutableStateOf<JobPost?>(null) }
    var selectedAssignedWorkerJob by remember { mutableStateOf<JobPost?>(null) }
    var pendingAction by remember { mutableStateOf<Pair<JobPost, String>?>(null) }

    val activeJobs = state.recentJobs.filter { it.status in setOf("Active", "Worker Assigned", "In Progress") }
    val completedJobs = state.recentJobs.filter { it.status == "Completed" }

    val filteredJobs = when (selectedTabIndex) {
        0 -> state.recentJobs
        1 -> activeJobs
        else -> completedJobs
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "My Jobs & Assigned Workers",
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
                selectedTab = ShopkeeperTab.JOBS,
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
            // Tabs Row
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
                            text = "All (${state.recentJobs.size})",
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
                            text = "Active (${activeJobs.size})",
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
                            text = "Completed (${completedJobs.size})",
                            fontSize = 14.sp,
                            fontWeight = if (selectedTabIndex == 2) FontWeight.Bold else FontWeight.Medium,
                            color = if (selectedTabIndex == 2) ErnoGreen else Color.Gray
                        )
                    }
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            if (state.isLoading) {
                CircularProgressIndicator(color = ErnoGreen, modifier = Modifier.padding(24.dp))
            } else if (state.errorMessage != null) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Text(state.errorMessage.orEmpty(), color = Color.DarkGray)
                    TextButton(onClick = onRefresh) { Text("Retry", color = ErnoGreen) }
                }
            } else if (filteredJobs.isEmpty()) {
                Box(
                    modifier = Modifier.fillMaxSize(),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "No jobs found",
                        fontSize = 14.sp,
                        color = Color.Gray
                    )
                }
            } else {
                LazyColumn(
                    modifier = Modifier
                        .fillMaxSize()
                        .padding(horizontal = 20.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    items(filteredJobs) { job ->
                        ShopkeeperJobManageCard(
                            job = job,
                            onViewWorkerProfile = { selectedAssignedWorkerJob = job },
                            onRateWorkerClick = { ratingJob = job },
                            onLifecycleAction = { action -> pendingAction = job to action },
                            onPayJob = { onPayJob(job.id) }
                        )
                    }
                    item {
                        Spacer(modifier = Modifier.height(16.dp))
                    }
                }
            }
        }
    }

    pendingAction?.let { (job, action) ->
        AlertDialog(
            onDismissRequest = { pendingAction = null },
            title = { Text(if (action == "complete") "Confirm completed work?" else "Cancel this job?") },
            text = { Text(if (action == "complete") "This marks ${job.title} as completed. No payment is processed." else "Workers will no longer be able to apply or continue this job.") },
            confirmButton = { TextButton(onClick = { onJobLifecycleAction(job.id, action); pendingAction = null }) { Text("Confirm") } },
            dismissButton = { TextButton(onClick = { pendingAction = null }) { Text("Keep job") } }
        )
    }

    // Rating Worker Dialog
    ratingJob?.let { job ->
        RatingDialog(
            title = "Rate Hired Worker",
            targetName = "Worker for ${job.title}",
            onDismiss = { ratingJob = null },
            onSubmitRating = { rating, comment ->
                onRateWorkerClick(job.id, rating, comment)
                ratingJob = null
            }
        )
    }

    // ASSIGNED WORKER PROFILE DIALOG
    selectedAssignedWorkerJob?.let { job ->
        val context = LocalContext.current
        val workerName = job.assignedWorkerName.ifBlank { "Aman" }

        AlertDialog(
            onDismissRequest = { selectedAssignedWorkerJob = null },
            containerColor = Color.White,
            titleContentColor = Color.Black,
            textContentColor = Color.Black,
            title = {
                Text(
                    text = "Assigned Worker Profile",
                    fontWeight = FontWeight.Bold,
                    fontSize = 18.sp,
                    color = Color.Black
                )
            },
            text = {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Box(
                            modifier = Modifier
                                .size(52.dp)
                                .background(Color(0xFFEAF5D8), CircleShape),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.Person,
                                contentDescription = null,
                                tint = ErnoGreen,
                                modifier = Modifier.size(28.dp)
                            )
                        }

                        Spacer(modifier = Modifier.width(12.dp))

                        Column {
                            Text(
                                text = workerName,
                                fontSize = 18.sp,
                                fontWeight = FontWeight.Bold,
                                color = Color.Black
                            )
                            Text(
                                text = "Accepted shift: ${job.title}",
                                fontSize = 12.sp,
                                color = Color.Gray
                            )
                        }
                    }

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
                                    modifier = Modifier.size(12.dp)
                                )
                                Spacer(modifier = Modifier.width(2.dp))
                                Text(
                                    text = "${job.assignedWorkerRating} ★ (${job.assignedWorkerShiftsCount} Shifts)",
                                    fontSize = 11.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color.Black
                                )
                            }
                        }
                    }

                    HorizontalDivider(color = Color(0xFFF0F0F0))

                    // Contact Actions
                    Button(
                        onClick = {
                            val intent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:${job.assignedWorkerPhone}"))
                            context.startActivity(intent)
                        },
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.buttonColors(containerColor = ErnoGreen),
                        shape = RoundedCornerShape(10.dp)
                    ) {
                        Icon(
                            imageVector = Icons.Default.Phone,
                            contentDescription = null,
                            tint = Color.White,
                            modifier = Modifier.size(16.dp)
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Call Worker (${job.assignedWorkerPhone})", fontWeight = FontWeight.Bold)
                    }

                    OutlinedButton(
                        onClick = {
                            val intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://wa.me/${job.assignedWorkerPhone.replace("+", "")}"))
                            context.startActivity(intent)
                        },
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(10.dp),
                        border = BorderStroke(1.dp, ErnoGreen)
                    ) {
                        Text("WhatsApp Chat Worker", color = ErnoGreen, fontWeight = FontWeight.Bold)
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { selectedAssignedWorkerJob = null }) {
                    Text("Close", color = Color.Gray)
                }
            }
        )
    }
}

@Composable
fun ShopkeeperJobManageCard(
    job: JobPost,
    onViewWorkerProfile: () -> Unit = {},
    onRateWorkerClick: () -> Unit = {},
    onLifecycleAction: (String) -> Unit = {},
    onPayJob: () -> Unit = {}
) {
    val maxPrice = job.payStructure.maxOfOrNull { it.price } ?: 349
    val isWorkerAssigned = job.isWorkerAssigned || job.assignedWorkerName.isNotBlank() || job.status in setOf("Worker Assigned", "In Progress")
    val assignedName = if (job.assignedWorkerName.isNotBlank()) job.assignedWorkerName else "Aman"

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
                Text(
                    text = job.title,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.Black
                )

                if (job.status == "In Progress") {
                    Surface(shape = RoundedCornerShape(12.dp), color = Color(0xFFFFF3E0)) {
                        Text("In Progress", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = Color(0xFFE65100), modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp))
                    }
                } else if (job.status == "Cancelled") {
                    Surface(shape = RoundedCornerShape(12.dp), color = Color(0xFFF1F1F1)) {
                        Text("Cancelled", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = Color.Gray, modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp))
                    }
                } else if (isWorkerAssigned) {
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = Color(0xFFEAF5D8)
                    ) {
                        Text(
                            text = "Worker Accepted ✓",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = ErnoGreen,
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                        )
                    }
                } else if (job.status == "Active") {
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = Color(0xFFE8F5E9)
                    ) {
                        Text(
                            text = "Active",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF2E7D32),
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                        )
                    }
                } else {
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = Color(0xFFEAF5D8)
                    ) {
                        Text(
                            text = "Work Completed",
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            color = ErnoGreen,
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(6.dp))

            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Default.LocationOn,
                    contentDescription = null,
                    tint = Color.Gray,
                    modifier = Modifier.size(14.dp)
                )
                Spacer(modifier = Modifier.width(4.dp))
                Text(
                    text = "${if (job.bookingType == "PRE_BOOKING") "Pre-Booking" else "Current Job"} • ${job.location} • Scheduled: ${job.scheduledDate}",
                    fontSize = 13.sp,
                    color = Color.Gray
                )
            }

            Spacer(modifier = Modifier.height(10.dp))
            if (job.status == "Active" && job.latitude != null && job.longitude != null) NearbyWorkersPanel(job)
            if (job.status in setOf("Worker Assigned", "In Progress")) AssignedWorkerTrackingPanel(job)

            // ASSIGNED WORKER PROFILE CARD BANNER
            if (isWorkerAssigned) {
                Surface(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { onViewWorkerProfile() },
                    shape = RoundedCornerShape(12.dp),
                    color = Color(0xFFF1F8E9),
                    border = BorderStroke(1.dp, Color(0xFFC8E6C9))
                ) {
                    Row(
                        modifier = Modifier.padding(12.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(36.dp)
                                    .background(ErnoGreen, CircleShape),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Person,
                                    contentDescription = null,
                                    tint = Color.White,
                                    modifier = Modifier.size(20.dp)
                                )
                            }
                            Spacer(modifier = Modifier.width(10.dp))
                            Column {
                                Text(
                                    text = "Worker Accepted: $assignedName",
                                    fontSize = 13.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color.Black
                                )
                                Text(
                                    text = "Rating: ${job.assignedWorkerRating} / 5.0 • Aadhaar Verified",
                                    fontSize = 11.sp,
                                    color = ErnoGreen,
                                    fontWeight = FontWeight.Medium
                                )
                            }
                        }

                        Text(
                            text = "View Profile",
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold,
                            color = ErnoGreen
                        )
                    }
                }

                Spacer(modifier = Modifier.height(10.dp))
            }

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Settlement Pay: ₹$maxPrice",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.Black
                )

                Text(
                    text = job.postedTime,
                    fontSize = 11.sp,
                    color = Color.Gray
                )
            }

            if (job.workerRating > 0) {
                Spacer(modifier = Modifier.height(8.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(
                        imageVector = Icons.Default.Star,
                        contentDescription = null,
                        tint = Color(0xFFFFB300),
                        modifier = Modifier.size(14.dp)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text(
                        text = "You rated worker: ${job.workerRating} ★",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.Black
                    )
                }
            }

            if (job.status == "Completed" || job.applicantsCount > 0 || isWorkerAssigned) {
                Spacer(modifier = Modifier.height(12.dp))
                HorizontalDivider(color = Color(0xFFF0F0F0))
                Spacer(modifier = Modifier.height(12.dp))

                OutlinedButton(
                    onClick = onViewWorkerProfile,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(44.dp),
                    shape = RoundedCornerShape(10.dp),
                    border = BorderStroke(1.dp, ErnoGreen)
                ) {
                    Icon(
                        imageVector = Icons.Default.Person,
                        contentDescription = null,
                        tint = ErnoGreen,
                        modifier = Modifier.size(16.dp)
                    )
                    Spacer(modifier = Modifier.width(4.dp))
                    Text("View Profile", fontSize = 12.sp, color = ErnoGreen, fontWeight = FontWeight.Bold)
                }
            }
            if (job.status == "In Progress" || job.status == "Worker Assigned" || job.status == "Active") {
                Spacer(modifier = Modifier.height(10.dp))
                when (job.status) {
                    "In Progress" -> Button(onClick = { onLifecycleAction("complete") }, modifier = Modifier.fillMaxWidth(), colors = ButtonDefaults.buttonColors(containerColor = ErnoGreen)) { Text("Confirm work completed") }
                    else -> OutlinedButton(onClick = { onLifecycleAction("cancel") }, modifier = Modifier.fillMaxWidth(), border = BorderStroke(1.dp, Color(0xFFB3261E))) { Text("Cancel job", color = Color(0xFFB3261E)) }
                }
            }
            if (job.status == "Completed") {
                Spacer(modifier = Modifier.height(10.dp))
                Button(onClick = onPayJob, modifier = Modifier.fillMaxWidth(), colors = ButtonDefaults.buttonColors(containerColor = ErnoGreen)) {
                    Text("View payment status / Pay with Razorpay")
                }
                Text("Payment is collected after completion is confirmed.", fontSize = 11.sp, color = Color.Gray)
            }
        }
    }
}


@Composable
private fun NearbyWorkersPanel(job: JobPost) {
    var radius by remember(job.id) { mutableFloatStateOf(5f) }
    var workers by remember(job.id) { mutableStateOf(emptyList<NearbyWorker>()) }
    var loading by remember(job.id) { mutableStateOf(false) }
    var error by remember(job.id) { mutableStateOf<String?>(null) }
    val scope=rememberCoroutineScope()
    fun refresh() { scope.launch { loading=true; error=null; try { workers=ErrnoMobileApi.nearbyWorkers(job.id,radius.toDouble()) } catch(e:Exception) { error=e.localizedMessage ?: "Nearby search unavailable" } finally { loading=false } } }
    Column(verticalArrangement=Arrangement.spacedBy(6.dp)) {
        Text("Nearby available workers · ${radius.toInt()} km",fontWeight=FontWeight.Bold,fontSize=13.sp)
        Slider(value=radius,onValueChange={radius=it},valueRange=1f..25f,steps=23)
        if(loading) CircularProgressIndicator(modifier=Modifier.size(20.dp),strokeWidth=2.dp,color=ErnoGreen)
        else if(error!=null) Text(error!!,fontSize=12.sp,color=Color(0xFFB3261E))
        else if(workers.isEmpty()) Text("No recently active available workers in this radius.",fontSize=12.sp,color=Color.Gray)
        else Text("${workers.size} eligible worker${if(workers.size==1)"" else "s"} · approximate locations",fontSize=12.sp,color=Color.Gray)
        WorkerLocationMapView(job.location,latitude=job.latitude,longitude=job.longitude,nearbyWorkers=workers)
        TextButton(onClick={refresh()}) { Text("Refresh nearby workers",color=ErnoGreen) }
    }
    LaunchedEffect(job.id,radius) { refresh() }
}

@Composable
private fun AssignedWorkerTrackingPanel(job: JobPost) {
    var coordinate by remember(job.id) { mutableStateOf<MapCoordinate?>(null) }
    var route by remember(job.id) { mutableStateOf<ApproximateRoute?>(null) }
    var state by remember(job.id) { mutableStateOf("connecting") }
    var updated by remember(job.id) { mutableStateOf<String?>(null) }
    var lastUpdateMillis by remember(job.id) { mutableStateOf(0L) }
    var error by remember(job.id) { mutableStateOf<String?>(null) }
    val scope=rememberCoroutineScope(); val lastRouteAt=remember(job.id){AtomicLong(0)}
    var lastRouted by remember(job.id) { mutableStateOf<MapCoordinate?>(null) }
    LaunchedEffect(job.id,job.status) {
        var backoff=1_000L; var terminal=false
        while(kotlinx.coroutines.currentCoroutineContext().isActive && !terminal) {
            val alive=AtomicBoolean(true); val ended=AtomicBoolean(false); var socket:WebSocket?=null
            try {
                socket=ErrnoMobileApi.openTrackingSocket(job.id,object:WebSocketListener(){
                    override fun onOpen(webSocket:WebSocket,response:okhttp3.Response){webSocket.send("heartbeat")}
                    override fun onMessage(webSocket:WebSocket,text:String){
                        val json=runCatching{JSONObject(text)}.getOrNull()?:return
                        scope.launch {
                            state=json.optString("state",state)
                            if(state=="ended")ended.set(true)
                            if(json.optString("type")=="heartbeat_ping" && lastUpdateMillis>0 && System.currentTimeMillis()-lastUpdateMillis>120_000) state="stale"
                            if(json.has("latitude")&&json.has("longitude")){
                                val next=MapCoordinate(json.getDouble("latitude"),json.getDouble("longitude")); coordinate=next; updated=json.optString("updated_at"); lastUpdateMillis=System.currentTimeMillis()
                                val previous=lastRouted
                                val distance=if(previous==null)Double.POSITIVE_INFINITY else FloatArray(1).also { android.location.Location.distanceBetween(previous.latitude,previous.longitude,next.latitude,next.longitude,it) }[0].toDouble()
                                val now=System.currentTimeMillis(); val last=lastRouteAt.get()
                                if(distance>=100 && now-last>30_000 && lastRouteAt.compareAndSet(last,now)) {
                                    lastRouted=next
                                    try { route=ErrnoMobileApi.trackingRoute(job.id) } catch(_:Exception) { route=null }
                                }
                            }
                        }
                    }
                    override fun onClosed(webSocket:WebSocket,code:Int,reason:String){alive.set(false)}
                    override fun onFailure(webSocket:WebSocket,t:Throwable,response:okhttp3.Response?){alive.set(false);scope.launch{state="disconnected";error="Tracking connection interrupted. Reconnecting…"}}
                })
                backoff=1_000L
                while(kotlinx.coroutines.currentCoroutineContext().isActive && alive.get() && !ended.get()) { delay(15_000); if(alive.get() && !socket.send("heartbeat")) alive.set(false) }
                terminal=ended.get()
            } catch(e:Exception){state="disconnected";error=e.localizedMessage ?: "Tracking unavailable";alive.set(false)}
            finally { socket?.close(1000,"tracking reconnect") }
            if(!terminal && kotlinx.coroutines.currentCoroutineContext().isActive){delay(backoff);backoff=(backoff*2).coerceAtMost(30_000L)}
        }
    }
    Column(verticalArrangement=Arrangement.spacedBy(6.dp)) {
        Text("Live worker tracking",fontWeight=FontWeight.Bold,fontSize=13.sp)
        Text("${state.replaceFirstChar { it.uppercase() }}${updated?.let { " · Updated $it" } ?: ""}",fontSize=11.sp,color=if(state=="online") ErnoGreen else Color.Gray)
        error?.let { Text(it,fontSize=11.sp,color=Color(0xFFB3261E)) }
        WorkerLocationMapView(job.location,latitude=job.latitude,longitude=job.longitude,workerLocation=coordinate,route=route)
        route?.let { Text("${it.distanceKm} km · about ${it.durationMinutes} min · approximate, no live traffic",fontSize=11.sp,color=Color.Gray) }
    }
}

package com.erno.app.ui.screens.notifications

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.platform.LocalContext
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.erno.app.data.repository.ErrnoMobileApi
import kotlinx.coroutines.launch
import org.json.JSONObject

@Composable
@OptIn(ExperimentalMaterial3Api::class)
fun NotificationInboxScreen(onBack: () -> Unit) {
    val context = LocalContext.current
    var showPermissionExplanation by remember { mutableStateOf(android.os.Build.VERSION.SDK_INT >= 33 && androidx.core.content.ContextCompat.checkSelfPermission(context, android.Manifest.permission.POST_NOTIFICATIONS) != android.content.pm.PackageManager.PERMISSION_GRANTED) }
    val permissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { showPermissionExplanation = false }
    val scope = rememberCoroutineScope()
    var notifications by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }
    var marketingEnabled by remember { mutableStateOf(false) }
    var nextCursor by remember { mutableStateOf<String?>(null) }
    suspend fun refresh() {
        loading = true; error = null
        runCatching { ErrnoMobileApi.notificationInbox() }.onSuccess { response ->
            val items = response.optJSONArray("items")
            notifications = (0 until (items?.length() ?: 0)).map { items!!.getJSONObject(it) }
            nextCursor = response.optString("nextCursor").takeIf { it.isNotBlank() && it != "null" }
        }.onFailure { error = it.localizedMessage ?: "Unable to load notifications" }
        loading = false
    }
    LaunchedEffect(Unit) { refresh() }
    LaunchedEffect(Unit) { marketingEnabled = runCatching { ErrnoMobileApi.notificationPreferences().optBoolean("marketing_enabled", false) }.getOrDefault(false) }
    if (showPermissionExplanation) AlertDialog(onDismissRequest={showPermissionExplanation=false}, title={Text("Stay updated")},
        text={Text("Allow notifications to receive booking, job, payment and verification updates. Your in-app inbox remains available if you skip." )},
        confirmButton={TextButton(onClick={showPermissionExplanation=false; permissionLauncher.launch(android.Manifest.permission.POST_NOTIFICATIONS)}) { Text("Continue") }},
        dismissButton={TextButton(onClick={showPermissionExplanation=false}) { Text("Not now") }})
    Scaffold(containerColor = Color(0xFF0B121F), topBar = {
        TopAppBar(title = { Text("Notifications") }, navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, null) } },
            actions = { IconButton(onClick = { scope.launch { refresh() } }) { Icon(Icons.Default.Refresh, "Refresh") } },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = Color(0xFF0B121F), titleContentColor = Color.White, navigationIconContentColor = Color.White, actionIconContentColor = Color.White))
    }) { padding ->
        when {
            loading && notifications.isEmpty() -> Box(Modifier.fillMaxSize().padding(padding), contentAlignment = androidx.compose.ui.Alignment.Center) { CircularProgressIndicator() }
            error != null && notifications.isEmpty() -> Column(Modifier.fillMaxSize().padding(padding).padding(24.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) { Text(error!!, color=Color.White); Button(onClick={scope.launch { refresh() }}) { Text("Retry") } }
            notifications.isEmpty() -> Box(Modifier.fillMaxSize().padding(padding), contentAlignment = androidx.compose.ui.Alignment.Center) { Text("You're all caught up", color=Color.White) }
            else -> LazyColumn(Modifier.fillMaxSize().padding(padding).padding(16.dp), verticalArrangement=Arrangement.spacedBy(10.dp)) {
                item { TextButton(onClick={ scope.launch { runCatching { ErrnoMobileApi.markAllNotificationsRead() }; refresh() } }) { Text("Mark all as read") } }
                item { Row(Modifier.fillMaxWidth(), horizontalArrangement=Arrangement.SpaceBetween) { Text("Promotional notifications", color=Color.White); Switch(checked=marketingEnabled,onCheckedChange={value->marketingEnabled=value;scope.launch { runCatching { ErrnoMobileApi.updateNotificationPreferences(JSONObject().put("marketing_enabled",value)) } }}) } }
                items(notifications, key={it.optString("id")}) { row ->
                    val read = !row.isNull("readAt")
                    Column(Modifier.fillMaxWidth().background(if(read) Color(0xFF182333) else Color(0xFF1C3440), RoundedCornerShape(14.dp)).clickable {
                        scope.launch { runCatching { ErrnoMobileApi.markNotificationRead(row.optString("id")) }; refresh() }
                    }.padding(16.dp), verticalArrangement=Arrangement.spacedBy(6.dp)) {
                        Text(row.optString("title"), color=Color.White, style=MaterialTheme.typography.titleMedium)
                        Text(row.optString("body"), color=Color(0xFFD4DBE4))
                        Text("${row.optString("category").replaceFirstChar { it.uppercase() }} · ${row.optString("createdAt")}", color=Color(0xFF9BA9B9), style=MaterialTheme.typography.labelSmall)
                    }
                }
                if (nextCursor != null) item {
                    TextButton(onClick={scope.launch {
                        runCatching { ErrnoMobileApi.notificationInbox(nextCursor) }.onSuccess { response ->
                            val rows=response.optJSONArray("items")
                            notifications=notifications+(0 until (rows?.length()?:0)).map { rows!!.getJSONObject(it) }
                            nextCursor=response.optString("nextCursor").takeIf { it.isNotBlank() && it!="null" }
                        }.onFailure { error=it.localizedMessage ?: "Unable to load more" }
                    }}) { Text("Load more") }
                }
            }
        }
    }
}

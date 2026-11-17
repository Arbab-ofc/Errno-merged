package com.erno.app.ui.screens.payment

import androidx.compose.foundation.layout.*
import android.net.Uri
import java.io.ByteArrayOutputStream
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import coil.compose.AsyncImage
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.DisposableEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.erno.app.MainActivity
import com.erno.app.data.repository.ErrnoMobileApi
import com.erno.app.data.repository.PaymentUiState
import kotlinx.coroutines.launch
import kotlinx.coroutines.CompletableDeferred
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import java.util.concurrent.atomic.AtomicBoolean
import org.json.JSONObject

@Composable
fun RazorpayPaymentScreen(bookingId: String, onBack: () -> Unit) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val scope = rememberCoroutineScope()
    val ui by PaymentUiState.state.collectAsState()
    var status by remember { mutableStateOf<JSONObject?>(null) }
    var order by remember { mutableStateOf<JSONObject?>(null) }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var message by remember { mutableStateOf<String?>(null) }
    var config by remember { mutableStateOf<JSONObject?>(null) }
    var selectedImage by remember { mutableStateOf<Uri?>(null) }
    var socketRef by remember { mutableStateOf<okhttp3.WebSocket?>(null) }
    var resumeGeneration by remember { mutableIntStateOf(0) }
    val imagePicker = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { selectedImage = it }
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event -> if (event == Lifecycle.Event.ON_RESUME) resumeGeneration++ }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }
    suspend fun refresh() {
        loading = true; error = null
        runCatching { ErrnoMobileApi.bookingPaymentStatus(bookingId) }
            .onSuccess { status = it }
            .onFailure { error = it.localizedMessage ?: "Payment status could not be loaded." }
        loading = false
    }
    LaunchedEffect(bookingId, resumeGeneration) {
        var backoff = 1_000L
        while (isActive) {
            refresh()
            runCatching { ErrnoMobileApi.paymentConfig() }.onSuccess { config = it }
            val disconnected = CompletableDeferred<Unit>()
            val opened = AtomicBoolean(false)
            var connectedAt = 0L
            val heartbeat = launch {
                while (isActive) {
                    delay(if (opened.get()) 20_000L else 30_000L)
                    if (opened.get()) socketRef?.send("heartbeat") else { refresh(); runCatching { ErrnoMobileApi.paymentConfig() }.onSuccess { config = it } }
                }
            }
            try {
                socketRef = ErrnoMobileApi.openPaymentSocket(object : okhttp3.WebSocketListener() {
                    override fun onOpen(webSocket: okhttp3.WebSocket, response: okhttp3.Response) {
                        socketRef = webSocket; opened.set(true); connectedAt = System.currentTimeMillis(); webSocket.send("heartbeat")
                        scope.launch { refresh(); runCatching { ErrnoMobileApi.paymentConfig() }.onSuccess { config = it } }
                    }
                    override fun onMessage(webSocket: okhttp3.WebSocket, text: String) {
                        runCatching { JSONObject(text) }.getOrNull()?.let { event ->
                            val type = event.optString("eventType")
                            val related = event.optString("bookingId") == bookingId
                            if (type == "payment_socket.ready" || type == "payment_config.updated" || (related && type.startsWith("manual_payment."))) {
                                scope.launch {
                                    refresh()
                                    if (type == "payment_config.updated") runCatching { ErrnoMobileApi.paymentConfig() }.onSuccess { config = it }
                                }
                            }
                        }
                    }
                    override fun onClosed(webSocket: okhttp3.WebSocket, code: Int, reason: String) { opened.set(false); disconnected.complete(Unit) }
                    override fun onFailure(webSocket: okhttp3.WebSocket, t: Throwable, response: okhttp3.Response?) { opened.set(false); disconnected.complete(Unit) }
                })
                disconnected.await()
            } catch (_: Exception) { disconnected.complete(Unit) }
            heartbeat.cancel()
            socketRef?.close(1000, "Payment screen closed"); socketRef = null
            if (connectedAt > 0 && System.currentTimeMillis() - connectedAt > 20_000L) backoff = 1_000L
            delay(backoff); backoff = (backoff * 2).coerceAtMost(30_000L)
        }
    }
    LaunchedEffect(ui, bookingId) { if (ui.bookingId == bookingId) refresh() }
    if (config?.optString("activeProvider") == "MANUAL_QR" || status?.optString("provider") == "MANUAL_QR") {
        val manual = config?.optJSONObject("manual")
        val submission = status?.optJSONObject("submission")
        val paymentStatus = if (status?.optString("status") == "PAID") "PAID" else submission?.optString("status") ?: status?.optString("status")
        Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Text("UPI payment", style = MaterialTheme.typography.headlineSmall)
            Text("Booking: $bookingId")
            status?.optInt("amountPaise")?.takeIf { it > 0 }?.let { Text("Payable: ₹%.2f".format(it / 100.0), style = MaterialTheme.typography.titleLarge) }
            when (paymentStatus) {
                "PAID" -> Text("Payment Successful", color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.titleLarge)
                "PENDING_REVIEW" -> Text("Payment screenshot submitted successfully. Waiting for admin verification.")
                "REJECTED" -> Text("Screenshot rejected: ${submission?.optString("rejectionReason") ?: "Please upload a new screenshot."}", color = MaterialTheme.colorScheme.error)
                else -> Unit
            }
            if (manual?.optBoolean("configured") == true) {
                manual.optString("qrImageUrl").takeIf { it.isNotBlank() }?.let { AsyncImage(model = it, contentDescription = "ERRNO UPI payment QR", modifier = Modifier.size(240.dp)) }
                manual.optString("merchantName").takeIf { it.isNotBlank() && it != "null" }?.let { Text("Payee: $it") }
                manual.optString("upiId").takeIf { it.isNotBlank() && it != "null" }?.let { Text("UPI ID: $it") }
                Text("Scan this QR code using any UPI app and complete the payment.")
                selectedImage?.let { AsyncImage(model = it, contentDescription = "Selected payment screenshot preview", modifier = Modifier.fillMaxWidth().heightIn(max = 280.dp)) }
                if (paymentStatus != "PENDING_REVIEW" && paymentStatus != "PAID") {
                    OutlinedButton(enabled = !loading, onClick = { imagePicker.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)) }) { Text(if (selectedImage == null) "Choose payment screenshot" else "Replace screenshot") }
                    Button(enabled = selectedImage != null && !loading, onClick = {
                        scope.launch {
                            loading = true; error = null
                            runCatching {
                                val uri = selectedImage!!
                                val bytes = context.contentResolver.openInputStream(uri)?.use { input ->
                                    val output = ByteArrayOutputStream(); val buffer = ByteArray(8192)
                                    while (true) {
                                        val count = input.read(buffer); if (count < 0) break
                                        require(output.size() + count <= 5 * 1024 * 1024) { "Choose an image smaller than 5 MB." }
                                        output.write(buffer, 0, count)
                                    }
                                    output.toByteArray()
                                } ?: error("Could not read selected image.")
                                val mime = context.contentResolver.getType(uri) ?: "image/jpeg"
                                ErrnoMobileApi.submitManualScreenshot(bookingId, bytes, mime)
                            }.onSuccess { message = "Payment screenshot submitted successfully. Waiting for admin verification."; selectedImage = null; refresh() }
                                .onFailure { error = it.localizedMessage ?: "Screenshot upload failed." }
                            loading = false
                        }
                    }) { Text(if (loading) "Uploading…" else "Submit for Verification") }
                }
            } else Text("UPI payment is temporarily unavailable. Please try again later.", color = MaterialTheme.colorScheme.error)
            if (!error.isNullOrBlank()) Text(error!!, color = MaterialTheme.colorScheme.error)
            OutlinedButton(enabled = !loading, onClick = { scope.launch { refresh() } }) { Text("Refresh payment status") }
            OutlinedButton(onClick = onBack) { Text("Back") }
        }
        return
    }
    Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("Job payment", style = MaterialTheme.typography.headlineSmall)
        Text("Payment is collected only after the shopkeeper confirms completed work.")
        Text("Booking: $bookingId")
        Text("Status: ${status?.optString("status", "PAYMENT_PENDING") ?: "Loading…"}")
        status?.optInt("amountPaise")?.takeIf { it > 0 }?.let { Text("Payable: ₹%.2f".format(it / 100.0)) }
        if (ui.bookingId == bookingId && !ui.message.isNullOrBlank()) Text(ui.message!!)
        if (!message.isNullOrBlank()) Text(message!!, color = MaterialTheme.colorScheme.primary)
        if (!error.isNullOrBlank()) Text(error!!, color = MaterialTheme.colorScheme.error)
        if (order == null && status?.optString("status") in setOf("PAYMENT_PENDING", "CASH_PENDING")) {
            OutlinedButton(enabled = !loading, onClick = {
                scope.launch {
                    loading = true
                    runCatching { ErrnoMobileApi.startCashCollection(bookingId) }
                        .onSuccess { message = "Cash collection awaits worker confirmation and Admin reconciliation."; refresh() }
                        .onFailure { error = it.localizedMessage ?: "Cash collection could not be started." }
                    loading = false
                }
            }) { Text("Record cash payment") }
        }
        Button(enabled = !loading && status?.optString("status") !in setOf("PAID", "REFUNDED"), onClick = {
            scope.launch {
                loading = true; error = null
                runCatching {
                    val paymentOrder = order ?: ErrnoMobileApi.createPaymentOrder(bookingId).also { order = it }
                    val activity = context as? MainActivity ?: error("Checkout is unavailable in this activity.")
                    activity.launchPaymentCheckout(paymentOrder, bookingId)
                }.onFailure { error = it.localizedMessage ?: "Unable to start payment." }
                loading = false
            }
        }) { Text(if (loading) "Loading…" else if (status?.optString("status") == "PAID") "Paid" else "Pay with Razorpay") }
        OutlinedButton(enabled = !loading, onClick = { scope.launch { refresh() } }) { Text("Refresh payment status") }
        OutlinedButton(onClick = onBack) { Text("Back") }
    }
}

package com.erno.app.ui.screens.payment

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.erno.app.MainActivity
import com.erno.app.data.repository.ErrnoMobileApi
import com.erno.app.data.repository.PaymentUiState
import kotlinx.coroutines.launch
import org.json.JSONObject

@Composable
fun RazorpayPaymentScreen(bookingId: String, onBack: () -> Unit) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val ui by PaymentUiState.state.collectAsState()
    var status by remember { mutableStateOf<JSONObject?>(null) }
    var order by remember { mutableStateOf<JSONObject?>(null) }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var message by remember { mutableStateOf<String?>(null) }
    suspend fun refresh() {
        loading = true; error = null
        runCatching { ErrnoMobileApi.bookingPaymentStatus(bookingId) }
            .onSuccess { status = it }
            .onFailure { error = it.localizedMessage ?: "Payment status could not be loaded." }
        loading = false
    }
    LaunchedEffect(bookingId) { refresh() }
    LaunchedEffect(ui, bookingId) { if (ui.bookingId == bookingId) refresh() }
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

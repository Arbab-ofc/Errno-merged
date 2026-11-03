package com.erno.app.ui.screens.worker

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import coil.compose.AsyncImage
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.erno.app.data.repository.ErrnoMobileApi
import com.erno.app.ui.components.WorkerBottomNavigation
import com.erno.app.ui.components.WorkerTab
import com.erno.app.ui.theme.ErnoGreen
import kotlinx.coroutines.launch
import org.json.JSONArray
import org.json.JSONObject

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WorkerEarningsScreen(state: WorkerState, onBackClick: () -> Unit, onNavigateTab: (WorkerTab) -> Unit) {
    val scope = rememberCoroutineScope()
    var wallet by remember { mutableStateOf<JSONObject?>(null) }
    var methods by remember { mutableStateOf<JSONArray?>(null) }
    var cashRows by remember { mutableStateOf<JSONArray?>(null) }
    var companyQrUrl by remember { mutableStateOf<String?>(null) }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }
    var message by remember { mutableStateOf<String?>(null) }
    suspend fun refresh() {
        loading = true; error = null
        runCatching { listOf(ErrnoMobileApi.workerWallet(), ErrnoMobileApi.payoutMethods(), ErrnoMobileApi.cashCollections(), ErrnoMobileApi.companyPaymentQr()) }
            .onSuccess { result -> wallet = result[0] as JSONObject; methods = result[1] as JSONArray; cashRows = result[2] as JSONArray
                val qr = result[3] as JSONObject; companyQrUrl = qr.optString("qrAssetUrl").takeIf { qr.optBoolean("configured") && it.startsWith("https://") } }
            .onFailure { error = it.localizedMessage ?: "Wallet data is unavailable." }
        loading = false
    }
    LaunchedEffect(Unit) { refresh() }
    val available = wallet?.optInt("availableBalancePaise") ?: 0
    val eligible = wallet?.optBoolean("withdrawalEligible") ?: false
    val eligibleMethod = methods?.let { rows -> (0 until rows.length()).map { rows.getJSONObject(it) }.firstOrNull { it.optString("status") == "VERIFIED" && it.optBoolean("kycVerified") } }
    Scaffold(topBar = {
        TopAppBar(title = { Text("Earnings & Wallet", color = Color.White, fontWeight = FontWeight.Bold) },
            navigationIcon = { IconButton(onClick = onBackClick) { Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back", tint = Color.White) } },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = Color(0xFF0B121F)))
    }, bottomBar = { WorkerBottomNavigation(selectedTab = WorkerTab.EARNINGS, onTabSelected = onNavigateTab, containerColor = Color(0xFF0E1726), contentColor = ErnoGreen) },
        containerColor = Color(0xFF0B121F)) { padding ->
        LazyColumn(Modifier.fillMaxSize().padding(padding).padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            if (loading) item { LinearProgressIndicator(Modifier.fillMaxWidth()) }
            if (error != null) item { Text(error!!, color = MaterialTheme.colorScheme.error); TextButton(onClick = { scope.launch { refresh() } }) { Text("Retry") } }
            if (message != null) item { Text(message!!, color = ErnoGreen) }
            wallet?.let { summary ->
                item {
                    Card { Column(Modifier.fillMaxWidth().padding(18.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("Available for withdrawal", style = MaterialTheme.typography.titleMedium)
                        Text(inr(available), style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
                        metric("Total earnings", summary.optInt("totalEarningsPaise"))
                        metric("Pending earnings", summary.optInt("pendingEarningsPaise"))
                        metric("Withdrawal pending", summary.optInt("withdrawalPendingPaise"))
                        metric("Withdrawn", summary.optInt("totalWithdrawnPaise"))
                        Text("Eligible paid jobs: ${summary.optInt("eligibleCompletedOrders")} / 3")
                        val reasons = summary.optJSONArray("eligibilityReasons")
                        if (reasons != null) for (i in 0 until reasons.length()) Text("• ${reasons.optString(i)}", color = Color.Gray, fontSize = 12.sp)
                        Button(enabled = eligible && eligibleMethod != null && !loading, onClick = {
                            scope.launch {
                                val method = eligibleMethod ?: return@launch
                                runCatching { ErrnoMobileApi.requestWithdrawal(available, method.getString("id")) }
                                    .onSuccess { message = "Withdrawal request ${it.optString("status")}; payout has not been sent yet."; refresh() }
                                    .onFailure { error = it.localizedMessage ?: "Withdrawal request failed." }
                            }
                        }, modifier = Modifier.fillMaxWidth()) { Text(if (eligibleMethod == null) "Verified payout method required" else "Request withdrawal") }
                        if (eligibleMethod == null) Text("Payout methods and KYC require Admin verification. Bank details are not stored in this app.", fontSize = 12.sp, color = Color.Gray)
                    } }
                }
                val pendingCash = cashRows ?: JSONArray()
                if (pendingCash.length() > 0) {
                    item { Text("Cash confirmation requests", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 18.sp) }
                    items((0 until pendingCash.length()).map { pendingCash.getJSONObject(it) }) { cash ->
                        Card { Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text("Booking ${cash.optString("bookingId")} · ${inr(cash.optInt("amountPaise"))}")
                            Text("Shopkeeper confirmed: ${cash.optBoolean("shopkeeperConfirmed")} · Status: ${cash.optString("status")}", fontSize = 12.sp)
                            if (!cash.optBoolean("workerConfirmed")) Button(onClick = {
                                scope.launch { runCatching { ErrnoMobileApi.confirmCashCollection(cash.getString("id")) }
                                    .onSuccess { message = "Cash receipt confirmed. Admin reconciliation remains pending."; refresh() }
                                    .onFailure { error = it.localizedMessage ?: "Unable to confirm cash receipt." } }
                            }) { Text("Confirm cash received") }
                        } }
                    }
                }
                item {
                    Card { Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("Pay ERRNO via UPI", fontWeight = FontWeight.Bold)
                        if (companyQrUrl != null) {
                            AsyncImage(model = companyQrUrl, contentDescription = "Verified ERRNO UPI QR", modifier = Modifier.size(220.dp))
                            Text("Scan to pay ERRNO via UPI. Reconcile the transaction in the app before treating it as settled.", fontSize = 13.sp, color = Color.Gray)
                        } else Text("Company QR is unavailable until ERRNO configures an approved YES BANK QR asset. Do not pay to an unverified destination.", fontSize = 13.sp, color = Color.Gray)
                        HorizontalDivider()
                        Text("Cash Collected", fontWeight = FontWeight.Bold)
                        metric("Cash collected", summary.optInt("cashCollectedPaise"))
                        metric("Unresolved settlement adjustment", summary.optInt("unresolvedSettlementAdjustmentsPaise"))
                    } }
                }
                item { Text("Wallet activity", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 18.sp) }
                val transactions = summary.optJSONArray("recentTransactions") ?: JSONArray()
                items((0 until transactions.length()).map { transactions.getJSONObject(it) }) { transaction ->
                    Card { Row(Modifier.fillMaxWidth().padding(14.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                        Column { Text(transaction.optString("category")); Text(transaction.optString("bookingId", "—"), fontSize = 11.sp, color = Color.Gray) }
                        Text(inr(transaction.optInt("amountPaise")), fontWeight = FontWeight.Bold)
                    } }
                }
            }
        }
    }
}

@Composable private fun metric(label: String, value: Int) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) { Text(label); Text(inr(value), fontWeight = FontWeight.SemiBold) }
}

private fun inr(paise: Int) = "₹" + "%.2f".format(paise / 100.0)

package com.erno.app

import android.os.Bundle
import android.content.Intent
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.lifecycle.lifecycleScope
import androidx.navigation.compose.rememberNavController
import androidx.navigation.NavHostController
import com.erno.app.data.repository.ErrnoMobileApi
import com.erno.app.data.repository.ErrnoSessionStore
import com.erno.app.data.repository.PaymentUiState
import com.erno.app.data.repository.PaymentUiStatus
import com.google.firebase.auth.FirebaseAuth
import com.razorpay.Checkout
import com.razorpay.PaymentData
import com.razorpay.PaymentResultWithDataListener
import org.json.JSONObject
import com.erno.app.navigation.NavGraph
import com.erno.app.ui.theme.ErnoTheme
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity(), PaymentResultWithDataListener {
    private var appNavController: NavHostController? = null
    private var presenceLoop: Job? = null
    private var pendingPaymentBookingId: String? = null
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        com.erno.app.notifications.ErrnoNotificationChannels.create(this)
        enableEdgeToEdge()
        Checkout.preload(applicationContext)
        setContent {
            ErnoTheme {
                val navController = rememberNavController()
                appNavController = navController
                NavGraph(navController = navController)
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        val signedIn = !ErrnoSessionStore.read().isNullOrBlank() || FirebaseAuth.getInstance().currentUser != null
        if (intent.hasExtra("notification_route") && signedIn) {
            appNavController?.navigate("notifications")
            intent.removeExtra("notification_route")
        }
    }

    fun launchPaymentCheckout(order: JSONObject, bookingId: String) {
        val options = JSONObject().apply {
            put("key", order.getString("keyId")); put("order_id", order.getString("razorpayOrderId"))
            put("amount", order.getInt("amountPaise")); put("currency", order.getString("currency"))
            put("name", "ERRNO"); put("description", "Completed job payment")
            put("notes", JSONObject().put("booking_id", bookingId))
        }
        pendingPaymentBookingId = bookingId
        PaymentUiState.update(PaymentUiStatus(bookingId, "CHECKOUT_OPEN", null))
        try { Checkout().open(this, options) }
        catch (error: Exception) { PaymentUiState.update(PaymentUiStatus(bookingId, "ORDER_CREATED", "Checkout could not be opened. Retry or refresh payment status.")) }
    }

    override fun onPaymentSuccess(paymentId: String?, paymentData: PaymentData?) {
        val bookingId = pendingPaymentBookingId ?: return
        val orderId = paymentData?.orderId
        val signature = paymentData?.signature
        if (paymentId.isNullOrBlank() || orderId.isNullOrBlank() || signature.isNullOrBlank()) {
            PaymentUiState.update(PaymentUiStatus(bookingId, "VERIFICATION_PENDING", "Checkout returned incomplete data. Refresh status.")); return
        }
        PaymentUiState.update(PaymentUiStatus(bookingId, "VERIFICATION_PENDING", "Verifying payment with ERRNO…"))
        lifecycleScope.launch {
            runCatching { ErrnoMobileApi.verifyPayment(bookingId, orderId, paymentId, signature) }
                .onSuccess { PaymentUiState.update(PaymentUiStatus(bookingId, it.optString("status"), "Payment status verified by ERRNO.")) }
                .onFailure { PaymentUiState.update(PaymentUiStatus(bookingId, "VERIFICATION_PENDING", "Payment verification is pending. Refresh status before retrying.")) }
        }
    }

    override fun onPaymentError(code: Int, response: String?, paymentData: PaymentData?) {
        val bookingId = pendingPaymentBookingId ?: return
        PaymentUiState.update(PaymentUiStatus(bookingId, "PAYMENT_PROCESSING", "Checkout closed or failed. Provider status may still update; refresh before retrying."))
    }

    override fun onResume() {
        super.onResume()
        startPresenceTracking()
    }

    fun startPresenceTracking() {
        if ((FirebaseAuth.getInstance().currentUser != null || ErrnoSessionStore.hasToken()) && presenceLoop == null) {
            presenceLoop = lifecycleScope.launch {
                while (FirebaseAuth.getInstance().currentUser != null || ErrnoSessionStore.hasToken()) {
                    val interval = runCatching { ErrnoMobileApi.presenceHeartbeat(true) }.getOrDefault(60)
                    delay(interval * 1_000L)
                }
            }
        }
    }

    override fun onPause() {
        stopPresenceTracking()
        if (FirebaseAuth.getInstance().currentUser != null || ErrnoSessionStore.hasToken()) lifecycleScope.launch { runCatching { ErrnoMobileApi.presenceOffline() } }
        super.onPause()
    }

    fun stopPresenceTracking() { presenceLoop?.cancel(); presenceLoop = null }
}

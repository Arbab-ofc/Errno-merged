package com.erno.app.notifications

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.erno.app.MainActivity
import com.erno.app.R
import com.erno.app.data.repository.ErrnoMobileApi
import com.erno.app.data.repository.ErrnoSessionStore
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.tasks.await
import java.util.UUID

class ErrnoFirebaseMessagingService : FirebaseMessagingService() {
    override fun onCreate() {
        super.onCreate()
        createChannels()
    }
    override fun onNewToken(token: String) {
        super.onNewToken(token)
        register(token)
    }

    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        // FCM notification payloads are displayed by Android while backgrounded. This branch
        // handles foreground data/notification messages only, avoiding a duplicate background alert.
        if (isForeground()) show(message.notification?.title ?: "ERRNO", message.notification?.body ?: "Open ERRNO for an update.", message.data)
    }

    private fun register(token: String) {
        if (ErrnoSessionStore.read().isNullOrBlank()) return
        CoroutineScope(Dispatchers.IO).launch {
            runCatching { ErrnoMobileApi.registerNotificationDevice("android", installId(this@ErrnoFirebaseMessagingService), token, packageManager.getPackageInfo(packageName, 0).versionName ?: "") }
        }
    }

    private fun installId(context: Context): String = context.getSharedPreferences("errno_push", 0).let { prefs ->
        prefs.getString("installation_id", null) ?: UUID.randomUUID().toString().also { prefs.edit().putString("installation_id", it).apply() }
    }

    private fun isForeground(): Boolean = getSystemService(android.app.ActivityManager::class.java).runningAppProcesses?.any {
        it.processName == packageName && it.importance == android.app.ActivityManager.RunningAppProcessInfo.IMPORTANCE_FOREGROUND
    } == true

    private fun show(title: String, body: String, data: Map<String, String>) {
        createChannels()
        val channel = when (data["route"]) {
            "payment" -> "errno_payments"
            "job" -> "errno_progress"
            "kyc", "account" -> "errno_account"
            else -> "errno_bookings"
        }
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP
            putExtra("notification_route", data["route"])
            putExtra("notification_job_id", data["job_id"] ?: data["booking_id"])
            putExtra("notification_payment_id", data["payment_id"])
            putExtra("notification_kyc_id", data["kyc_profile_id"])
        }
        val pending = PendingIntent.getActivity(this, (data["notification_id"] ?: UUID.randomUUID().toString()).hashCode(), intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
        val notification = NotificationCompat.Builder(this, channel).setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle(title.take(180)).setContentText(body.take(500)).setContentIntent(pending).setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH).build()
        runCatching { NotificationManagerCompat.from(this).notify((data["notification_id"] ?: UUID.randomUUID().toString()).hashCode(), notification) }
    }

    private fun createChannels() {
        ErrnoNotificationChannels.create(this)
    }
}

object ErrnoNotificationChannels {
    fun create(context: Context) {
        if (Build.VERSION.SDK_INT < 26) return
        val manager = context.getSystemService(NotificationManager::class.java)
        listOf(
            NotificationChannel("errno_bookings", "Booking Updates", NotificationManager.IMPORTANCE_HIGH),
            NotificationChannel("errno_progress", "Job Progress", NotificationManager.IMPORTANCE_DEFAULT),
            NotificationChannel("errno_payments", "Payments", NotificationManager.IMPORTANCE_HIGH),
            NotificationChannel("errno_account", "Account & Verification", NotificationManager.IMPORTANCE_DEFAULT),
            NotificationChannel("errno_promotions", "Promotions", NotificationManager.IMPORTANCE_LOW),
        ).forEach(manager::createNotificationChannel)
    }
}

object ErrnoNotificationDeviceSync {
    private fun preferences() = com.google.firebase.FirebaseApp.getInstance().applicationContext.getSharedPreferences("errno_push", 0)
    fun installIdentifier(): String = preferences().let { prefs ->
        prefs.getString("installation_id", null) ?: UUID.randomUUID().toString().also { prefs.edit().putString("installation_id", it).apply() }
    }
    suspend fun registerCurrent() {
        if (ErrnoSessionStore.read().isNullOrBlank() && com.google.firebase.auth.FirebaseAuth.getInstance().currentUser == null) return
        val token = FirebaseMessaging.getInstance().token.await()
        val result = ErrnoMobileApi.registerNotificationDevice("android", installIdentifier(), token, "1.0")
        preferences().edit().putString("server_device_id", result.getString("deviceId")).apply()
    }
    suspend fun unregisterCurrent() {
        val prefs = preferences()
        prefs.getString("server_device_id", null)?.let { runCatching { ErrnoMobileApi.unregisterNotificationDevice(it) } }
        prefs.edit().remove("server_device_id").apply()
    }
}

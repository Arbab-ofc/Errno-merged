package com.erno.app.data.repository

import com.erno.app.BuildConfig
import com.erno.app.data.model.DurationPay
import com.erno.app.data.model.JobPost
import com.erno.app.data.model.WorkerJob
import com.erno.app.data.model.WorkerApplication
import com.google.firebase.auth.FirebaseAuth
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.tasks.await
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.time.LocalDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale

/** Backend opaque sessions or verified Firebase tokens. Firebase ID tokens are never persisted here. */
object ErrnoMobileApi {
    private suspend fun request(method: String, path: String, body: JSONObject? = null): String = withContext(Dispatchers.IO) {
        val sessionToken = ErrnoSessionStore.read()
        val user = FirebaseAuth.getInstance().currentUser
        val token = sessionToken ?: (user?.getIdToken(false)?.await()?.token) ?: error("Sign in to continue.")
        val base = BuildConfig.ERRNO_API_BASE_URL.trimEnd('/')
        check(base.startsWith("https://") || (BuildConfig.DEBUG && (base.startsWith("http://10.0.2.2") || base.startsWith("http://localhost")))) { "Backend URL is not configured securely." }
        val connection = (URL(base + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            instanceFollowRedirects = false
            connectTimeout = 15_000
            readTimeout = 20_000
            setRequestProperty("Accept", "application/json")
            setRequestProperty("Authorization", "Bearer $token")
            if (body != null) { doOutput = true; setRequestProperty("Content-Type", "application/json") }
        }
        try {
            body?.let { connection.outputStream.bufferedWriter().use { writer -> writer.write(it.toString()) } }
            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val text = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
            check(code in 200..299) { when (code) { 401 -> "Your session expired. Sign in again."; 403 -> "This action is not allowed for your account."; 404 -> "This record is no longer available."; 409 -> "This record changed. Refresh and try again."; else -> "Backend request failed ($code)." } }
            text
        } finally { connection.disconnect() }
    }

    suspend fun availableJobs(): List<WorkerJob> {
        val array = JSONArray(request("GET", "/jobs?status_filter=open"))
        return (0 until array.length()).map { array.getJSONObject(it).toWorkerJob() }
    }

    suspend fun myJobs(): List<JobPost> {
        val array = JSONArray(request("GET", "/jobs/mine"))
        return (0 until array.length()).map { array.getJSONObject(it).toShopkeeperJob() }
    }

    suspend fun workerJobs(): List<WorkerJob> {
        val array = JSONArray(request("GET", "/jobs/worker/mine"))
        return (0 until array.length()).map { array.getJSONObject(it).toWorkerJob() }
    }

    suspend fun workerApplications(limit: Int = 20, offset: Int = 0): JSONObject =
        JSONObject(request("GET", "/jobs/applications/me?limit=$limit&offset=$offset"))

    private val presenceSessionId: String by lazy {
        val preferences = com.google.firebase.FirebaseApp.getInstance().applicationContext.getSharedPreferences("errno_presence", 0)
        preferences.getString("session_id", null) ?: java.util.UUID.randomUUID().toString().also { preferences.edit().putString("session_id", it).apply() }
    }
    suspend fun presenceHeartbeat(foreground: Boolean = true): Int {
        return JSONObject(request("POST", "/api/v1/presence/heartbeat", JSONObject().put("session_identifier", presenceSessionId)
            .put("device_platform", "android").put("is_foreground", foreground))).getInt("heartbeat_interval_seconds")
    }
    suspend fun presenceOffline() {
        request("POST", "/api/v1/presence/offline", JSONObject().put("session_identifier", presenceSessionId)
            .put("device_platform", "android").put("is_foreground", false))
    }
    suspend fun setWorkerAvailable(available: Boolean) {
        request("PATCH", "/api/v1/workers/me/availability", JSONObject().put("available", available))
    }
    suspend fun workerAvailability(): Boolean = JSONObject(request("GET", "/api/v1/workers/me/availability")).optBoolean("available")
    suspend fun workerPayout(jobId: String): JSONObject = JSONObject(request("GET", "/api/v1/jobs/$jobId/worker-payout"))

    suspend fun cancelApplication(jobId: String) { request("DELETE", "/jobs/$jobId/applications/me") }
    suspend fun startJob(jobId: String) { request("POST", "/jobs/$jobId/start") }
    suspend fun completeJob(jobId: String) { request("POST", "/jobs/$jobId/complete") }
    suspend fun cancelJob(jobId: String) { request("PATCH", "/jobs/$jobId/status?new_status=cancelled") }

    suspend fun requestPricingQuote(hours: Int, scheduledDate: String, areaKey: String?): JSONObject {
        val parsed = runCatching {
            LocalDateTime.parse(scheduledDate, DateTimeFormatter.ofPattern("dd MMM yyyy 'at' hh:mm a", Locale.ENGLISH))
        }.getOrElse { error("Select a service date and time before requesting a price quote.") }
        val start = parsed.atZone(ZoneId.systemDefault()).toOffsetDateTime().toString()
        return JSONObject(request("POST", "/api/v1/pricing/quotes", JSONObject()
            .put("duration_hours", hours).put("service_start_at", start).put("area_id", areaKey ?: JSONObject.NULL)))
    }

    suspend fun postJob(job: JobPost, quoteId: String, serviceStartAt: String): JobPost {
        val pay = job.payStructure.firstOrNull() ?: error("Pricing is not configured for a duration. Contact support.")
        val body = JSONObject().put("title", job.title).put("category", job.category)
            .put("description", job.description).put("pay_amount", pay.price)
            .put("duration_type", "${pay.hours} hours").put("scheduled_date", job.scheduledDate)
            .put("location", job.location).put("pickup_location", job.pickupLocation)
            .put("drop_location", job.dropLocation).put("is_delivery", job.isDeliveryJob)
            .put("quote_id", quoteId).put("service_start_at", serviceStartAt)
        return JSONObject(request("POST", "/jobs", body)).toShopkeeperJob()
    }

    suspend fun pricingDurations(): List<DurationPay> {
        val rows = JSONArray(request("GET", "/api/v1/pricing/durations"))
        return (0 until rows.length()).mapNotNull { index ->
            val row = rows.getJSONObject(index)
            if (!row.optBoolean("enabled") || row.optString("approval_status") != "approved") return@mapNotNull null
            val maximum = row.optDouble("maximum_price", Double.NaN)
            if (!maximum.isFinite()) return@mapNotNull null
            DurationPay(row.getInt("duration_hours"), maximum.toInt())
        }
    }

    suspend fun apply(jobId: String) { request("POST", "/jobs/$jobId/apply") }

    suspend fun ownerApplications(): List<JSONObject> {
        val array = JSONArray(request("GET", "/jobs/applications/owner"))
        return (0 until array.length()).map { array.getJSONObject(it) }
    }

    suspend fun saveShop(name: String, address: String, category: String): JSONObject = JSONObject(request(
        "PUT", "/shops/me", JSONObject().put("shop_name", name).put("address", address).put("category", category)
    ))

    suspend fun profile(): JSONObject = JSONObject(request("GET", "/api/v1/users/me"))
    suspend fun updateProfile(name: String): JSONObject = JSONObject(request("PATCH", "/api/v1/users/me", JSONObject().put("name", name)))
    suspend fun shop(): JSONObject? {
        val body = request("GET", "/shops/me")
        return if (body.trim() == "null") null else JSONObject(body)
    }

    suspend fun decideApplication(jobId: String, applicationId: String, decision: String) {
        request("PATCH", "/jobs/$jobId/applications/$applicationId", JSONObject().put("decision", decision))
    }

    private fun JSONObject.toShopkeeperJob(): JobPost {
        val amount = optDouble("pay_amount", 0.0).toInt()
        val hours = optString("duration_type").filter { it.isDigit() }.toIntOrNull() ?: 1
        return JobPost(id = getString("id"), title = getString("title"), category = optString("category"),
            location = optString("location"), description = optString("description"), payStructure = listOf(DurationPay(hours, amount)),
            status = when (optString("status")) { "assigned" -> "Worker Assigned"; "in_progress" -> "In Progress"; "completed" -> "Completed"; "cancelled" -> "Cancelled"; else -> "Active" },
            isDeliveryJob = optBoolean("is_delivery"), pickupLocation = optString("pickup_location"),
            dropLocation = optString("drop_location"), scheduledDate = optString("scheduled_date"), isWorkerAssigned = optString("assigned_worker_id").isNotBlank())
    }

    private fun JSONObject.toWorkerJob(): WorkerJob {
        val amount = optDouble("pay_amount", 0.0).toInt()
        val hours = optString("duration_type").filter { it.isDigit() }.toIntOrNull() ?: 1
        val apiStatus = optString("status")
        val displayStatus = when (apiStatus) {
            "assigned" -> "Upcoming"
            "in_progress" -> "Ongoing"
            "completed" -> "Completed"
            "cancelled" -> "Cancelled"
            else -> "Available"
        }
        return WorkerJob(id = getString("id"), title = getString("title"), location = optString("location"), distance = "",
            description = optString("description"), payStructure = listOf(DurationPay(hours, amount)), selectedHours = hours,
            selectedPay = amount, status = displayStatus, isDeliveryJob = optBoolean("is_delivery"), pickupLocation = optString("pickup_location"),
            dropLocation = optString("drop_location"), scheduledDate = optString("scheduled_date"))
    }

    fun parseWorkerApplication(json: JSONObject): WorkerApplication {
        val application = json
        val job = application.getJSONObject("job")
        val shop = job.optJSONObject("shop")
        return WorkerApplication(
            id = application.getString("id"), jobId = application.getString("job_id"), status = application.getString("status"),
            createdAt = application.optString("created_at"), jobTitle = job.optString("title"),
            jobStatus = job.optString("status"), location = job.optString("location"),
            scheduledDate = job.optString("scheduled_date"), payAmount = job.optDouble("pay_amount").toInt(),
            shopName = shop?.optString("shop_name").orEmpty(), shopAddress = shop?.optString("address").orEmpty()
        )
    }
}

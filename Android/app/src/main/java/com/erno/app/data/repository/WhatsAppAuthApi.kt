package com.erno.app.data.repository

import com.erno.app.BuildConfig
import com.google.firebase.FirebaseApp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL

data class WhatsAppOtpChallenge(val requestId: String, val expiresInSeconds: Int, val resendAfterSeconds: Int)
data class WhatsAppIdentity(val id: String, val role: String)

object WhatsAppAuthApi {
    private suspend fun request(path: String, body: JSONObject, bearer: String? = null): JSONObject = withContext(Dispatchers.IO) {
        val base = BuildConfig.ERRNO_API_BASE_URL.trimEnd('/')
        check(base.startsWith("https://") || (BuildConfig.DEBUG && (base.startsWith("http://10.0.2.2") || base.startsWith("http://localhost")))) { "Use HTTPS for the ERRNO backend." }
        val connection = (URL(base + path).openConnection() as HttpURLConnection).apply {
            requestMethod = "POST"; connectTimeout = 15_000; readTimeout = 20_000; doOutput = true
            setRequestProperty("Accept", "application/json"); setRequestProperty("Content-Type", "application/json")
            bearer?.let { setRequestProperty("Authorization", "Bearer $it") }
        }
        try {
            connection.outputStream.bufferedWriter().use { it.write(body.toString()) }
            val code = connection.responseCode
            val stream = if (code in 200..299) connection.inputStream else connection.errorStream
            val response = JSONObject(stream?.bufferedReader()?.use { it.readText() }.orEmpty().ifBlank { "{}" })
            check(code in 200..299) {
                val detail = response.opt("detail")
                when {
                    code == 429 -> if (detail is JSONObject) detail.optString("message", "Please wait before trying again.") else "Please wait before trying again."
                    detail is JSONObject -> detail.optString("message", "WhatsApp OTP request failed.")
                    detail is String -> detail
                    else -> "WhatsApp OTP request failed ($code)."
                }
            }
            response
        } finally { connection.disconnect() }
    }

    suspend fun send(phone: String, role: String): WhatsAppOtpChallenge {
        val e164 = phoneE164(phone)
        val result = request("/api/v1/auth/whatsapp/send-otp", JSONObject().put("phone", e164).put("role", role.uppercase()))
        return WhatsAppOtpChallenge(result.getString("requestId"), result.getInt("expiresInSeconds"), result.getInt("resendAfterSeconds"))
    }
    suspend fun resend(phone: String, role: String, requestId: String): WhatsAppOtpChallenge {
        val result = request("/api/v1/auth/whatsapp/resend-otp", JSONObject().put("phone", phoneE164(phone)).put("role", role.uppercase()).put("requestId", requestId))
        return WhatsAppOtpChallenge(result.getString("requestId"), result.getInt("expiresInSeconds"), result.getInt("resendAfterSeconds"))
    }
    suspend fun verify(phone: String, role: String, requestId: String, otp: String, fullName: String? = null): WhatsAppIdentity {
        val body = JSONObject().put("phone", phoneE164(phone)).put("role", role.uppercase()).put("requestId", requestId).put("otp", otp)
        fullName?.trim()?.takeIf { it.isNotEmpty() }?.let { body.put("fullName", it) }
        val result = request("/api/v1/auth/whatsapp/verify-otp", body)
        ErrnoSessionStore.save(result.getString("accessToken"))
        val user = result.getJSONObject("user")
        return WhatsAppIdentity(user.getString("id"), user.getString("role"))
    }
    suspend fun logout() {
        val token = ErrnoSessionStore.read() ?: return
        runCatching { request("/api/v1/auth/whatsapp/logout", JSONObject(), token) }
        ErrnoSessionStore.clear()
    }
    private fun phoneE164(raw: String): String {
        val digits = raw.filter(Char::isDigit)
        val phone = if (digits.length == 10) "+91$digits" else if (raw.startsWith("+")) "+$digits" else error("Enter a valid phone number.")
        require(phone.length in 9..16) { "Enter a valid phone number." }
        return phone
    }
}

package com.erno.app.data.repository

import android.app.Activity
import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import com.erno.app.BuildConfig
import com.google.android.libraries.identity.googleid.GetGoogleIdOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.firebase.auth.FirebaseAuth
import com.google.firebase.auth.GoogleAuthProvider
import kotlinx.coroutines.tasks.await
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

data class ErrnoIdentity(val id: String, val role: String?, val onboardingCompleted: Boolean)

/** Google Credential Manager -> Firebase -> verified Firebase ID token -> ERRNO API. */
object FirebaseGoogleAuth {
    suspend fun signIn(activity: Activity, selectedRole: String): ErrnoIdentity {
        val clientIdName = "default_web_client_id"
        val resourceId = activity.resources.getIdentifier(clientIdName, "string", activity.packageName)
        check(resourceId != 0) { "Google OAuth web client is missing. Configure OAuth in Firebase and download google-services.json again." }
        val option = GetGoogleIdOption.Builder()
            .setServerClientId(activity.getString(resourceId))
            .setFilterByAuthorizedAccounts(false)
            .setAutoSelectEnabled(false)
            .build()
        val request = GetCredentialRequest.Builder().addCredentialOption(option).build()
        val credential = CredentialManager.create(activity).getCredential(activity, request).credential
        check(credential is CustomCredential && credential.type == GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL) {
            "Google did not return a valid sign-in credential. Please try again."
        }
        val googleToken = GoogleIdTokenCredential.createFrom(credential.data).idToken
        val firebaseCredential = GoogleAuthProvider.getCredential(googleToken, null)
        val user = FirebaseAuth.getInstance().signInWithCredential(firebaseCredential).await().user
            ?: error("Firebase sign-in did not return a user.")
        try {
            val firebaseToken = user.getIdToken(true).await().token ?: error("Firebase did not return an ID token.")
            return syncWithBackend(firebaseToken, selectedRole)
        } catch (error: Exception) {
            FirebaseAuth.getInstance().signOut()
            throw error
        }
    }

    suspend fun restore(): ErrnoIdentity? = withContext(Dispatchers.IO) {
        val user = FirebaseAuth.getInstance().currentUser ?: return@withContext null
        val token = user.getIdToken(true).await().token ?: error("Firebase did not return an ID token.")
        syncWithBackend(token, null)
    }

    suspend fun logout() {
        val user = FirebaseAuth.getInstance().currentUser
        if (user != null && BuildConfig.ERRNO_API_BASE_URL.isNotBlank()) {
            runCatching {
                val token = user.getIdToken(false).await().token ?: return@runCatching
                request("POST", "/api/v1/auth/logout", token)
            }
        }
        FirebaseAuth.getInstance().signOut()
    }

    private suspend fun syncWithBackend(token: String, selectedRole: String?): ErrnoIdentity = withContext(Dispatchers.IO) {
        check(BuildConfig.ERRNO_API_BASE_URL.isNotBlank()) { "ERRNO_API_BASE_URL is not configured for this build." }
        var user = request("POST", "/api/v1/auth/firebase", token).getJSONObject("user")
        if (user.isNull("role") && selectedRole != null) {
            user = request("PATCH", "/api/v1/users/me", token, JSONObject().put("role", selectedRole))
        }
        ErrnoIdentity(
            id = user.getString("id"),
            role = user.optString("role").takeUnless { it.isBlank() || it == "null" },
            onboardingCompleted = user.optBoolean("onboarding_completed", false)
        )
    }

    private fun request(method: String, path: String, token: String, body: JSONObject? = null): JSONObject {
        val base = BuildConfig.ERRNO_API_BASE_URL.trimEnd('/')
        require(base.startsWith("https://") || (BuildConfig.DEBUG && (base.startsWith("http://10.0.2.2") || base.startsWith("http://localhost")))) {
            "Use HTTPS for the ERRNO backend."
        }
        val connection = (URL(base + path).openConnection() as HttpURLConnection).apply {
            requestMethod = method
            instanceFollowRedirects = false
            connectTimeout = 15_000
            readTimeout = 20_000
            setRequestProperty("Accept", "application/json")
            setRequestProperty("Authorization", "Bearer $token")
            if (body != null) {
                doOutput = true
                setRequestProperty("Content-Type", "application/json")
            }
        }
        try {
            body?.let { payload -> connection.outputStream.bufferedWriter().use { it.write(payload.toString()) } }
            val status = connection.responseCode
            val stream = if (status in 200..299) connection.inputStream else connection.errorStream
            val response = stream?.bufferedReader()?.use { it.readText() }.orEmpty()
            check(status in 200..299) { if (status == 401) "ERRNO authentication failed. Please sign in again." else "ERRNO backend request failed ($status)." }
            return JSONObject(response)
        } finally {
            connection.disconnect()
        }
    }
}

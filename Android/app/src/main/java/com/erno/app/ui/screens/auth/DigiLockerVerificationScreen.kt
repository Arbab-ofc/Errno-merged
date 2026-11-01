package com.erno.app.ui.screens.auth

import android.content.Intent
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.erno.app.data.repository.ErrnoMobileApi
import kotlinx.coroutines.launch
import org.json.JSONObject

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DigiLockerVerificationScreen(
    isAlreadyVerified: Boolean = false,
    onBackClick: () -> Unit,
    onStatusRefreshed: () -> Unit = {}
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var status by remember { mutableStateOf<JSONObject?>(null) }
    var selectedType by remember { mutableStateOf("") }
    var consent by remember { mutableStateOf(false) }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var notice by remember { mutableStateOf<String?>(null) }
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) scope.launch {
            busy = true
            try {
                val mime = context.contentResolver.getType(uri) ?: "application/octet-stream"
                val bytes = context.contentResolver.openInputStream(uri)?.use { input -> input.readNBytes(8 * 1024 * 1024 + 1) } ?: error("Unable to read the selected document.")
                val version = status?.optString("consentVersion", "v1") ?: "v1"
                val result = ErrnoMobileApi.uploadKyc(selectedType, version, bytes, mime)
                notice = "Document submitted for manual review (${result.optString("status")}). It has not been verified by DigiLocker."
                refreshKycStatus { status = it }
            } catch (e: Exception) { error = e.localizedMessage ?: "Document submission failed." }
            finally { busy = false }
        }
    }
    fun run(action: suspend () -> JSONObject, done: (JSONObject) -> Unit = { status = it }) {
        scope.launch { busy = true; error = null; try { done(action()) } catch (e: Exception) { error = e.localizedMessage ?: "Request failed." } finally { busy = false } }
    }
    LaunchedEffect(Unit) { runCatching { ErrnoMobileApi.kycStatus() }.onSuccess { status = it; onStatusRefreshed() }.onFailure { error = it.localizedMessage ?: "Unable to load verification status." } }
    val available = status?.optJSONArray("availableDocumentTypes")
    if (selectedType.isBlank() && available != null && available.length() > 0) selectedType = available.optString(0)
    Scaffold(topBar = { TopAppBar(title = { Text("Identity verification") }, navigationIcon = { IconButton(onClick = onBackClick) { Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back") } }) }) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).verticalScroll(rememberScrollState()).padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Text("Status: ${status?.optString("status") ?: if (isAlreadyVerified) "Loading" else "Not started"}", style = MaterialTheme.typography.titleLarge)
            Text("Verification method: ${status?.optString("verificationMethod").takeUnless { it.isNullOrBlank() || it == "null" } ?: "Not verified"}")
            Text("ERRNO uses identity information only for worker onboarding and eligibility review. Results are restricted to authorized reviewers and retained under the configured policy. DigiLocker authentication happens outside ERRNO; never share your password, PIN, or OTP with us.")
            Text("Available document categories: ${if (available == null || available.length() == 0) "Not configured" else (0 until available.length()).joinToString { available.optString(it) }}")
            Row { Checkbox(consent, { consent = it }); Text("I consent to the selected document category being used for ERRNO identity verification.", modifier = Modifier.padding(top = 12.dp)) }
            Button(enabled = consent && !busy && status?.optBoolean("digilockerEnabled") == true, onClick = {
                val values = if (selectedType.isBlank()) emptyList() else listOf(selectedType)
                run({ ErrnoMobileApi.startKyc(values, status?.optString("consentVersion", "v1") ?: "v1") }) { response ->
                    status = JSONObject().put("status", response.optString("status"))
                    val url = response.optString("authorizationUrl")
                    if (url.startsWith("https://")) context.startActivity(Intent(Intent.ACTION_VIEW, android.net.Uri.parse(url)))
                    else notice = "DigiLocker requester integration is not configured. No verification session was started."
                }
            }) { Text("Continue with DigiLocker") }
            if (status?.optBoolean("manualReviewEnabled") == true) {
                Text("Manual document review is available as a separate ERRNO review process. A manual approval is not represented as official DigiLocker verification.")
                Button(enabled = consent && !busy && selectedType.isNotBlank(), onClick = { picker.launch(arrayOf("application/pdf", "image/jpeg", "image/png")) }) { Text("Submit for manual review") }
            }
            OutlinedButton(enabled = !busy, onClick = { run({ ErrnoMobileApi.kycStatus() }) { status = it; onStatusRefreshed() } }) { Text("Refresh status") }
            TextButton(enabled = !busy, onClick = { run({ ErrnoMobileApi.withdrawKycConsent() }) { status = it; notice = "Consent withdrawn." } }) { Text("Withdraw consent") }
            if (busy) CircularProgressIndicator()
            error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            notice?.let { Text(it) }
        }
    }
}

private suspend fun refreshKycStatus(onStatus: (JSONObject) -> Unit) { onStatus(ErrnoMobileApi.kycStatus()) }

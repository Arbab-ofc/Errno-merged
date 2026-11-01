package com.erno.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.lifecycle.lifecycleScope
import androidx.navigation.compose.rememberNavController
import com.erno.app.data.repository.ErrnoMobileApi
import com.erno.app.data.repository.ErrnoSessionStore
import com.google.firebase.auth.FirebaseAuth
import com.erno.app.navigation.NavGraph
import com.erno.app.ui.theme.ErnoTheme
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {
    private var presenceLoop: Job? = null
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            ErnoTheme {
                val navController = rememberNavController()
                NavGraph(navController = navController)
            }
        }
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

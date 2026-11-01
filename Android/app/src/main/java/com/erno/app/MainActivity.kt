package com.erno.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.lifecycle.lifecycleScope
import androidx.navigation.compose.rememberNavController
import com.erno.app.data.repository.ErrnoMobileApi
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
        if (FirebaseAuth.getInstance().currentUser != null && presenceLoop == null) {
            presenceLoop = lifecycleScope.launch {
                while (FirebaseAuth.getInstance().currentUser != null) {
                    val interval = runCatching { ErrnoMobileApi.presenceHeartbeat(true) }.getOrDefault(60)
                    delay(interval * 1_000L)
                }
            }
        }
    }

    override fun onPause() {
        presenceLoop?.cancel(); presenceLoop = null
        if (FirebaseAuth.getInstance().currentUser != null) lifecycleScope.launch { runCatching { ErrnoMobileApi.presenceOffline() } }
        super.onPause()
    }
}

package com.erno.app.ui.screens.worker

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class WorkerSessionResetTest {
    @Test
    fun resetSessionClearsWorkerStateOnAccountSwitch() {
        val viewModel = WorkerViewModel()
        viewModel.toggleOnlineStatus(false)
        assertFalse(viewModel.uiState.value.isOnline)

        viewModel.resetSession()

        assertTrue(viewModel.uiState.value.isOnline)
        assertFalse(viewModel.uiState.value.isAvailableForWork)
        assertEquals("Worker", viewModel.uiState.value.workerName)
        assertTrue(viewModel.uiState.value.preferredSkills.isEmpty())
        assertTrue(viewModel.uiState.value.myJobs.isEmpty())
    }
}

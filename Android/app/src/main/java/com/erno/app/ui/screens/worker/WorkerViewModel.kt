package com.erno.app.ui.screens.worker

import androidx.lifecycle.ViewModel
import com.erno.app.data.model.DurationPay
import com.erno.app.data.model.EarningRecord
import com.erno.app.data.model.JobPost
import com.erno.app.data.model.WorkerJob
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

data class WorkerState(
    val workerName: String = "Worker",
    val currentLocation: String = "Okhla Market Area",
    val totalEarnings: Int = 0, // Starts at 0 for new workers
    val jobsCompletedCount: Int = 0, // Starts at 00
    val jobApprovalsCount: Int = 0, // Starts at 00
    val workerRating: Float = 0.0f, // Starts at 0.0 rating for everyone initially
    val isDigiLockerVerified: Boolean = false,
    val aadhaarMasked: String = "",
    val availableJobs: List<WorkerJob> = emptyList(), // Starts empty for new logins
    val selectedJob: WorkerJob? = null,
    val myJobs: List<WorkerJob> = emptyList(), // Starts empty for new logins
    val earningsHistory: List<EarningRecord> = emptyList() // Starts empty for new logins
)

class WorkerViewModel : ViewModel() {
    private val _uiState = MutableStateFlow(WorkerState())
    val uiState: StateFlow<WorkerState> = _uiState.asStateFlow()

    fun selectJob(job: WorkerJob) {
        _uiState.update { it.copy(selectedJob = job) }
    }

    fun selectDurationPay(hours: Int, pay: Int) {
        _uiState.update { state ->
            val currentJob = state.selectedJob ?: return@update state
            state.copy(selectedJob = currentJob.copy(selectedHours = hours, selectedPay = pay))
        }
    }

    fun acceptCurrentJob() {
        val state = _uiState.value
        val currentJob = state.selectedJob ?: return
        // Set status directly to ONGOING when worker accepts job
        val acceptedJob = currentJob.copy(status = "Ongoing", scheduledTime = "${currentJob.scheduledDate}, 11:00 AM")
        _uiState.update {
            it.copy(
                selectedJob = acceptedJob,
                myJobs = listOf(acceptedJob) + it.myJobs.filter { j -> j.id != acceptedJob.id }
            )
        }
    }

    fun completeWorkerJob(jobTitle: String, payAmount: Int) {
        _uiState.update { state ->
            val updatedMyJobs = state.myJobs.map { job ->
                if (job.title.contains(jobTitle, ignoreCase = true) || job.status == "Ongoing" || job.status == "Upcoming") {
                    job.copy(status = "Completed")
                } else job
            }
            val newEarnings = state.totalEarnings + payAmount
            val newEarningRecord = EarningRecord(
                id = System.currentTimeMillis().toString(),
                jobTitle = jobTitle.ifBlank { "Completed Shift" },
                hours = "Completed",
                date = "Today",
                amount = payAmount
            )
            state.copy(
                myJobs = updatedMyJobs,
                totalEarnings = newEarnings,
                jobsCompletedCount = state.jobsCompletedCount + 1,
                earningsHistory = listOf(newEarningRecord) + state.earningsHistory
            )
        }
    }

    fun verifyDigiLockerAadhaar(aadhaarNumber: String) {
        val last4 = if (aadhaarNumber.length >= 4) aadhaarNumber.takeLast(4) else "1234"
        _uiState.update {
            it.copy(
                isDigiLockerVerified = true,
                aadhaarMasked = "XXXX-XXXX-$last4"
            )
        }
    }

    fun rateShopkeeper(jobId: String, rating: Float, comment: String) {
        _uiState.update { state ->
            val updatedJobs = state.myJobs.map { job ->
                if (job.id == jobId) job.copy(shopkeeperRating = rating, reviewComment = comment) else job
            }
            state.copy(myJobs = updatedJobs)
        }
    }

    fun addJobFromShopkeeper(job: JobPost) {
        val newWorkerJob = WorkerJob(
            id = job.id,
            title = job.title,
            location = job.location,
            distance = "1.2 km away",
            description = job.description,
            isNew = true,
            payStructure = job.payStructure,
            selectedHours = job.payStructure.firstOrNull()?.hours ?: 1,
            selectedPay = job.payStructure.firstOrNull()?.price ?: 149,
            status = "Available",
            scheduledTime = "${job.scheduledDate}, 10:00 AM",
            isDeliveryJob = job.isDeliveryJob,
            pickupLocation = job.pickupLocation,
            dropLocation = job.dropLocation,
            packageType = job.packageType,
            scheduledDate = job.scheduledDate
        )
        _uiState.update {
            it.copy(
                availableJobs = listOf(newWorkerJob) + it.availableJobs.filter { j -> j.id != newWorkerJob.id }
            )
        }
    }
}

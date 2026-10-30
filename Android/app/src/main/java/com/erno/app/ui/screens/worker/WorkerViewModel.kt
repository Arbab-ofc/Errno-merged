package com.erno.app.ui.screens.worker

import androidx.lifecycle.ViewModel
import com.erno.app.data.model.DurationPay
import com.erno.app.data.model.EarningRecord
import com.erno.app.data.model.JobPost
import com.erno.app.data.model.WorkerJob
import com.erno.app.data.model.WorkerApplication
import com.erno.app.data.repository.ErrnoMobileApi
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
    val applications: List<WorkerApplication> = emptyList(),
    val applicationsOffset: Int = 0,
    val applicationsHasMore: Boolean = false,
    val isLoadingApplications: Boolean = false,
    val applicationsError: String? = null,
    val lifecycleActionLoading: Boolean = false,
    val earningsHistory: List<EarningRecord> = emptyList(), // Starts empty for new logins
    val isLoadingJobs: Boolean = false,
    val jobLoadError: String? = null
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

    suspend fun refreshBackendJobs() {
        _uiState.update { it.copy(isLoadingJobs = true, jobLoadError = null) }
        runCatching { ErrnoMobileApi.availableJobs() }
            .onSuccess { jobs ->
                val mine = runCatching { ErrnoMobileApi.workerJobs() }.getOrDefault(emptyList())
                _uiState.update { it.copy(availableJobs = jobs, myJobs = mine, isLoadingJobs = false) }
            }
            .onFailure { error -> _uiState.update { it.copy(isLoadingJobs = false, jobLoadError = error.localizedMessage ?: "Unable to load jobs. Retry.") } }
    }

    suspend fun refreshApplications() {
        _uiState.update { it.copy(isLoadingApplications = true, applicationsError = null, applicationsOffset = 0) }
        runCatching { ErrnoMobileApi.workerApplications(limit = 20, offset = 0) }
            .onSuccess { page ->
                val items = page.getJSONArray("items")
                _uiState.update { it.copy(
                    applications = (0 until items.length()).map { index -> ErrnoMobileApi.parseWorkerApplication(items.getJSONObject(index)) },
                    applicationsOffset = items.length(), applicationsHasMore = page.optBoolean("has_more"),
                    isLoadingApplications = false
                ) }
            }
            .onFailure { error -> _uiState.update { it.copy(isLoadingApplications = false, applicationsError = error.localizedMessage ?: "Unable to load applications. Retry.") } }
    }

    suspend fun loadMoreApplications() {
        if (_uiState.value.applications.isEmpty() || _uiState.value.applicationsError != null) {
            refreshApplications()
            return
        }
        val offset = _uiState.value.applicationsOffset
        if (!_uiState.value.applicationsHasMore || _uiState.value.isLoadingApplications) return
        _uiState.update { it.copy(isLoadingApplications = true, applicationsError = null) }
        runCatching { ErrnoMobileApi.workerApplications(limit = 20, offset = offset) }
            .onSuccess { page ->
                val items = page.getJSONArray("items")
                _uiState.update { state -> state.copy(
                    applications = state.applications + (0 until items.length()).map { ErrnoMobileApi.parseWorkerApplication(items.getJSONObject(it)) },
                    applicationsOffset = offset + items.length(), applicationsHasMore = page.optBoolean("has_more"), isLoadingApplications = false
                ) }
            }
            .onFailure { error -> _uiState.update { it.copy(isLoadingApplications = false, applicationsError = error.localizedMessage ?: "Unable to load more applications.") } }
    }

    suspend fun cancelApplication(application: WorkerApplication) {
        _uiState.update { it.copy(lifecycleActionLoading = true, applicationsError = null) }
        try {
            ErrnoMobileApi.cancelApplication(application.jobId)
            refreshApplications()
        } catch (error: Exception) {
            _uiState.update { it.copy(applicationsError = error.localizedMessage ?: "Unable to cancel application.") }
        } finally { _uiState.update { it.copy(lifecycleActionLoading = false) } }
    }

    suspend fun startAssignedJob(jobId: String) {
        _uiState.update { it.copy(lifecycleActionLoading = true, jobLoadError = null) }
        try { ErrnoMobileApi.startJob(jobId); refreshBackendJobs() }
        catch (error: Exception) { _uiState.update { it.copy(jobLoadError = error.localizedMessage ?: "Unable to start job.") } }
        finally { _uiState.update { it.copy(lifecycleActionLoading = false) } }
    }

    suspend fun acceptCurrentJob() {
        val state = _uiState.value
        val currentJob = state.selectedJob ?: return
        ErrnoMobileApi.apply(currentJob.id)
        val acceptedJob = currentJob.copy(status = "Applied", scheduledTime = "${currentJob.scheduledDate}, 11:00 AM")
        _uiState.update {
            it.copy(
                selectedJob = acceptedJob,
                availableJobs = it.availableJobs.filterNot { job -> job.id == acceptedJob.id },
                jobLoadError = null
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

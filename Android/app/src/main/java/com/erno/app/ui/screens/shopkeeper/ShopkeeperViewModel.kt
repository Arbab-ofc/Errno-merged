package com.erno.app.ui.screens.shopkeeper

import androidx.lifecycle.ViewModel
import com.erno.app.data.model.DurationPay
import com.erno.app.data.model.JobPost
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

data class ShopkeeperState(
    val ownerName: String = "Shopkeeper",
    val activeJobsCount: Int = 0,
    val totalApplicationsCount: Int = 0,
    val recentJobs: List<JobPost> = emptyList(), // Starts empty for new login
    // Draft job for creation
    val draftTitle: String = "Delivery Partner",
    val draftCategory: String = "Delivery Partner",
    val draftLocation: String = "Okhla Market Area",
    val draftPickupLocation: String = "Okhla Market Store #12",
    val draftDropLocation: String = "Sector 18 Noida",
    val draftPackageType: String = "Parcel / Product Box",
    val draftIsDelivery: Boolean = true,
    val draftScheduledDate: String = "Today",
    val draftDescription: String = "Deliver parcel/products safely from shop to target location.",
    val draftPayStructure: List<DurationPay> = listOf(DurationPay(2, 249)), // Single duration selection
    val lastPostedJob: JobPost? = null
)

class ShopkeeperViewModel : ViewModel() {
    private val _uiState = MutableStateFlow(ShopkeeperState())
    val uiState: StateFlow<ShopkeeperState> = _uiState.asStateFlow()

    fun updateTitle(title: String) {
        _uiState.update { it.copy(draftTitle = title) }
    }

    fun updateCategory(category: String) {
        val isDelivery = category.equals("Delivery Partner", ignoreCase = true) || category.contains("Delivery", ignoreCase = true)
        _uiState.update {
            it.copy(
                draftCategory = category,
                draftTitle = category,
                draftIsDelivery = isDelivery
            )
        }
    }

    fun updateLocation(location: String) {
        _uiState.update { it.copy(draftLocation = location) }
    }

    fun updatePickupLocation(pickup: String) {
        _uiState.update { it.copy(draftPickupLocation = pickup) }
    }

    fun updateDropLocation(drop: String) {
        _uiState.update { it.copy(draftDropLocation = drop) }
    }

    fun updatePackageType(packageType: String) {
        _uiState.update { it.copy(draftPackageType = packageType) }
    }

    fun updateScheduledDate(date: String) {
        _uiState.update { it.copy(draftScheduledDate = date) }
    }

    fun updateDescription(description: String) {
        _uiState.update { it.copy(draftDescription = description) }
    }

    fun rateWorker(jobId: String, rating: Float, comment: String) {
        _uiState.update { state ->
            val updatedJobs = state.recentJobs.map { job ->
                if (job.id == jobId) job.copy(workerRating = rating, reviewComment = comment) else job
            }
            state.copy(recentJobs = updatedJobs)
        }
    }

    fun assignWorkerToJob(jobId: String, workerName: String) {
        _uiState.update { state ->
            val updatedJobs = state.recentJobs.map { job ->
                if (job.id == jobId || job.status == "Active") {
                    job.copy(
                        status = "Worker Assigned",
                        isWorkerAssigned = true,
                        assignedWorkerName = workerName.ifBlank { "Aman" },
                        assignedWorkerPhone = "+919876543210",
                        assignedWorkerRating = 4.8f,
                        assignedWorkerShiftsCount = 14
                    )
                } else job
            }
            state.copy(recentJobs = updatedJobs)
        }
    }

    fun completeJobPayment(jobTitle: String) {
        _uiState.update { state ->
            val updatedJobs = state.recentJobs.map { job ->
                if (job.title.contains(jobTitle, ignoreCase = true) || job.status == "Worker Assigned" || job.status == "Active") {
                    job.copy(status = "Completed")
                } else job
            }
            state.copy(
                recentJobs = updatedJobs,
                activeJobsCount = maxOf(0, state.activeJobsCount - 1)
            )
        }
    }

    fun resetDraft() {
        _uiState.update {
            it.copy(
                draftTitle = "Delivery Partner",
                draftCategory = "Delivery Partner",
                draftLocation = "Okhla Market Area",
                draftPickupLocation = "Okhla Market Store #12",
                draftDropLocation = "Sector 18 Noida",
                draftPackageType = "Parcel / Product Box",
                draftIsDelivery = true,
                draftScheduledDate = "Today",
                draftDescription = "Deliver parcel/products safely from shop to target location.",
                draftPayStructure = listOf(DurationPay(2, 249))
            )
        }
    }

    fun toggleDurationPay(hours: Int, defaultPrice: Int) {
        _uiState.update { state ->
            state.copy(draftPayStructure = listOf(DurationPay(hours, defaultPrice)))
        }
    }

    fun removeDurationPay(item: DurationPay) {
        _uiState.update { state ->
            itCopy(state, draftPayStructure = state.draftPayStructure.filter { dp -> dp.hours != item.hours })
        }
    }

    fun updatePrice(hours: Int, newPrice: Int) {
        _uiState.update { state ->
            val updated = state.draftPayStructure.map {
                if (it.hours == hours) it.copy(price = newPrice) else it
            }
            itCopy(state, draftPayStructure = updated)
        }
    }

    fun addDurationPay(hours: Int, price: Int) {
        _uiState.update { state ->
            itCopy(state, draftPayStructure = listOf(DurationPay(hours, price)))
        }
    }

    fun postJob(): JobPost {
        val state = _uiState.value
        val computedLocation = if (state.draftIsDelivery) {
            "${state.draftPickupLocation.ifBlank { "Pickup Store" }} -> ${state.draftDropLocation.ifBlank { "Drop Address" }}"
        } else {
            state.draftLocation.ifBlank { "Okhla Market Area" }
        }

        val newJob = JobPost(
            id = System.currentTimeMillis().toString(),
            title = state.draftTitle.ifBlank { "Delivery Partner" },
            category = state.draftCategory.ifBlank { "Delivery Partner" },
            location = computedLocation,
            description = state.draftDescription.ifBlank { "Deliver parcel/products safely." },
            payStructure = if (state.draftPayStructure.isNotEmpty()) state.draftPayStructure else listOf(DurationPay(2, 249)),
            status = "Active",
            postedTime = "Posted just now",
            applicantsCount = 0,
            isDeliveryJob = state.draftIsDelivery,
            pickupLocation = state.draftPickupLocation,
            dropLocation = state.draftDropLocation,
            packageType = state.draftPackageType,
            scheduledDate = state.draftScheduledDate
        )
        _uiState.update {
            it.copy(
                recentJobs = listOf(newJob) + it.recentJobs,
                activeJobsCount = it.activeJobsCount + 1,
                lastPostedJob = newJob
            )
        }
        return newJob
    }

    private fun itCopy(state: ShopkeeperState, draftPayStructure: List<DurationPay>): ShopkeeperState {
        return state.copy(draftPayStructure = draftPayStructure)
    }
}

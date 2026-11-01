package com.erno.app.ui.screens.shopkeeper

import androidx.lifecycle.ViewModel
import com.erno.app.data.model.DurationPay
import com.erno.app.data.model.JobPost
import com.erno.app.data.repository.ErrnoMobileApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update

data class ShopkeeperState(
    val ownerName: String = "Shopkeeper",
    val shopName: String = "My Store",
    val shopAddress: String = "",
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
    val draftPayStructure: List<DurationPay> = emptyList(), // Loaded from the backend pricing configuration
    val pricingOptions: List<DurationPay> = emptyList(),
    val pricingQuote: Map<String, String> = emptyMap(),
    val lastPostedJob: JobPost? = null,
    val isLoading: Boolean = false,
    val errorMessage: String? = null
)

class ShopkeeperViewModel : ViewModel() {
    private val _uiState = MutableStateFlow(ShopkeeperState())
    val uiState: StateFlow<ShopkeeperState> = _uiState.asStateFlow()

    fun setError(message: String) { _uiState.update { it.copy(errorMessage = message, pricingQuote = emptyMap()) } }

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
                draftPayStructure = emptyList()
            )
        }
    }

    fun toggleDurationPay(hours: Int, defaultPrice: Int) {
        _uiState.update { state ->
            val configured = state.pricingOptions.firstOrNull { it.hours == hours } ?: return@update state
            state.copy(draftPayStructure = listOf(configured))
        }
    }

    fun removeDurationPay(item: DurationPay) {
        _uiState.update { state ->
            itCopy(state, draftPayStructure = state.draftPayStructure.filter { dp -> dp.hours != item.hours })
        }
    }

    fun updatePrice(hours: Int, newPrice: Int) {
        // Customer prices are read-only values supplied by the backend.
    }

    fun addDurationPay(hours: Int, price: Int) {
        _uiState.update { state ->
            val configured = state.pricingOptions.firstOrNull { it.hours == hours } ?: return@update state
            itCopy(state, draftPayStructure = listOf(configured))
        }
    }

    suspend fun refreshJobs() {
        _uiState.update { it.copy(isLoading = true, errorMessage = null) }
        runCatching { ErrnoMobileApi.myJobs() }
            .onSuccess { jobs -> _uiState.update { it.copy(recentJobs = jobs, activeJobsCount = jobs.count { job -> job.status == "Active" }, isLoading = false) } }
            .onFailure { error -> _uiState.update { it.copy(isLoading = false, errorMessage = error.localizedMessage ?: "Unable to load jobs. Retry.") } }
    }

    suspend fun updateJobLifecycle(jobId: String, action: String) {
        _uiState.update { it.copy(isLoading = true, errorMessage = null) }
        try {
            when (action) {
                "complete" -> ErrnoMobileApi.completeJob(jobId)
                "cancel" -> ErrnoMobileApi.cancelJob(jobId)
                else -> error("Unsupported job action")
            }
            refreshJobs()
        } catch (error: Exception) {
            _uiState.update { it.copy(isLoading = false, errorMessage = error.localizedMessage ?: "Unable to update job.") }
            throw error
        }
    }

    suspend fun refreshProfile() {
        runCatching {
            val profile = ErrnoMobileApi.profile()
            val shop = ErrnoMobileApi.shop()
            _uiState.update { it.copy(ownerName = profile.optString("name", "Shopkeeper"),
                shopName = shop?.optString("shop_name", "My Store") ?: "My Store",
                shopAddress = shop?.optString("address", "") ?: "") }
        }.onFailure { error -> _uiState.update { it.copy(errorMessage = error.localizedMessage ?: "Unable to load profile.") } }
    }

    suspend fun refreshPricing() {
        runCatching { ErrnoMobileApi.pricingDurations() }.onSuccess { configured ->
            _uiState.update { state ->
                val selected = configured.firstOrNull { it.hours == state.draftPayStructure.firstOrNull()?.hours } ?: configured.firstOrNull()
                state.copy(pricingOptions = configured, draftPayStructure = listOfNotNull(selected))
            }
        }.onFailure { error -> _uiState.update { it.copy(errorMessage = error.localizedMessage ?: "Pricing configuration is unavailable.") } }
    }

    suspend fun saveProfile(name: String, storeName: String) {
        val updatedProfile = ErrnoMobileApi.updateProfile(name.trim())
        val updatedShop = ErrnoMobileApi.saveShop(storeName.trim(), _uiState.value.shopAddress, "General Store")
        _uiState.update { it.copy(ownerName = updatedProfile.optString("name"), shopName = updatedShop.optString("shop_name"), errorMessage = null) }
    }

    suspend fun postJob(): JobPost {
        val state = _uiState.value
        val quoteId = state.pricingQuote["quote_id"] ?: error("Request a current price quote before confirming the job.")
        val quoteServiceStart = state.pricingQuote["service_start_at"] ?: error("The pricing quote has no service time.")
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
            payStructure = state.draftPayStructure,
            status = "Active",
            postedTime = "Posted just now",
            applicantsCount = 0,
            isDeliveryJob = state.draftIsDelivery,
            pickupLocation = state.draftPickupLocation,
            dropLocation = state.draftDropLocation,
            packageType = state.draftPackageType,
            scheduledDate = state.draftScheduledDate
        )
        val persisted = ErrnoMobileApi.postJob(newJob, quoteId, quoteServiceStart)
        _uiState.update {
            it.copy(
                recentJobs = listOf(persisted) + it.recentJobs,
                activeJobsCount = it.activeJobsCount + 1,
                lastPostedJob = persisted,
                errorMessage = null
            )
        }
        return persisted
    }

    suspend fun refreshQuote() {
        val state = _uiState.value
        val hours = state.draftPayStructure.firstOrNull()?.hours ?: error("Select a configured duration first.")
        val areaKey = if (state.draftIsDelivery) state.draftPickupLocation.ifBlank { "Pickup Store" } else state.draftLocation.ifBlank { "Okhla Market Area" }
        val quote = ErrnoMobileApi.requestPricingQuote(hours, state.draftScheduledDate, areaKey)
        val fields = listOf("quote_id", "service_start_at", "final_service_charge", "base_price", "time_multiplier", "demand_multiplier", "commission_amount", "worker_payout_amount", "expires_at")
        _uiState.update { it.copy(pricingQuote = fields.associateWith { key -> quote.optString(key) }, errorMessage = null) }
    }

    private fun itCopy(state: ShopkeeperState, draftPayStructure: List<DurationPay>): ShopkeeperState {
        return state.copy(draftPayStructure = draftPayStructure)
    }
}

package com.erno.app.ui.screens.shopkeeper

import androidx.lifecycle.ViewModel
import com.erno.app.data.model.DurationPay
import com.erno.app.data.model.JobPost
import com.erno.app.data.repository.ErrnoMobileApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import java.text.ParsePosition
import java.text.SimpleDateFormat
import java.util.Calendar
import java.util.Locale

fun todayIsoDate(): String = SimpleDateFormat("yyyy-MM-dd", Locale.ROOT).format(Calendar.getInstance().time)

fun getFormattedTodayDate(): String {
    val displayFormat = SimpleDateFormat("EEE, d MMM yyyy", Locale.getDefault())
    return displayFormat.format(Calendar.getInstance().time)
}

fun getAvailablePreBookingDates(): List<Pair<String, String>> {
    val today = Calendar.getInstance().apply {
        set(Calendar.HOUR_OF_DAY, 0)
        set(Calendar.MINUTE, 0)
        set(Calendar.SECOND, 0)
        set(Calendar.MILLISECOND, 0)
    }
    val isoFormat = SimpleDateFormat("yyyy-MM-dd", Locale.ROOT)
    val displayFormat = SimpleDateFormat("EEE, d MMM", Locale.getDefault())

    return (1..7).map { offset ->
        val cal = (today.clone() as Calendar).apply {
            add(Calendar.DAY_OF_YEAR, offset)
        }
        val iso = isoFormat.format(cal.time)
        val display = displayFormat.format(cal.time)
        iso to display
    }
}

data class CategorySuggestion(
    val description: String,
    val requirements: String
)

fun getCategorySuggestion(category: String): CategorySuggestion {
    return when {
        category.contains("Loading", ignoreCase = true) || category.contains("Unloading", ignoreCase = true) -> CategorySuggestion(
            description = "Workers are required for loading and unloading goods, materials, or packages. The work may involve lifting, carrying, arranging, and moving items at the specified location.",
            requirements = "• Ability to handle physical demands\n• Comfortable with loading and unloading materials\n• Follow workplace safety instructions\n• Arrive at specified location on time"
        )
        category.contains("Delivery", ignoreCase = true) -> CategorySuggestion(
            description = "Safely pick up parcels, packages, or store items and deliver them to designated customer addresses or target locations promptly.",
            requirements = "• Valid driving license & vehicle (if applicable)\n• Knowledge of local routes & navigation\n• Punctual and customer-friendly behavior\n• Handle parcels with care"
        )
        category.contains("Counter", ignoreCase = true) || category.contains("Cashier", ignoreCase = true) -> CategorySuggestion(
            description = "Manage customer checkout, operate payment counters, handle billing inquiries, and maintain accurate sales receipts.",
            requirements = "• Basic math & billing knowledge\n• Friendly customer interaction\n• Attention to detail\n• Punctual & reliable"
        )
        category.contains("Packing", ignoreCase = true) -> CategorySuggestion(
            description = "Pack, label, inspect, and bundle items or order parcels efficiently according to shop guidelines for store delivery or dispatch.",
            requirements = "• Good hand dexterity & speed\n• Careful packaging skills\n• Follow packing checklists\n• Maintain order accuracy"
        )
        category.contains("Cleaning", ignoreCase = true) || category.contains("Maintenance", ignoreCase = true) -> CategorySuggestion(
            description = "Maintain shop cleanliness, sweep, mop, sanitize work areas, dispose of trash, and ensure a clean environment.",
            requirements = "• Basic cleanliness knowledge\n• Detail-oriented & diligent\n• Follow safety & sanitation guidelines\n• Punctual & reliable"
        )
        else -> CategorySuggestion(
            description = "Assist shop staff with daily store operations, inventory stocking, organizing shelves, customer service, and general shop maintenance.",
            requirements = "• Active & energetic attitude\n• Basic communication skills\n• Punctual & honest\n• Ready to assist with shop tasks"
        )
    }
}

data class ShopkeeperState(
    val ownerName: String = "Shopkeeper",
    val shopName: String = "My Store",
    val shopAddress: String = "",
    val activeJobsCount: Int = 0,
    val totalApplicationsCount: Int = 0,
    val recentJobs: List<JobPost> = emptyList(), // Starts empty for new login
    // Draft job for creation
    val draftTitle: String = "Loading & Unloading",
    val draftCategory: String = "Loading & Unloading",
    val draftLocation: String = "Okhla Market Area",
    val draftPickupLocation: String = "Okhla Market Store #12",
    val draftDropLocation: String = "Sector 18 Noida",
    val draftPackageType: String = "Parcel / Product Box",
    val draftIsDelivery: Boolean = false,
    val draftWorkerCount: Int = 1,
    val draftScheduledDate: String = todayIsoDate(),
    val draftBookingType: String = "CURRENT", // "CURRENT" or "PRE_BOOKING"
    val draftWorkingRequirementType: String = "IMMEDIATE", // "IMMEDIATE" or "DYNAMIC_TIME"
    val draftScheduledTime: String = "Immediate",
    val draftSubmitted: Boolean = false,
    val draftDescription: String = getCategorySuggestion("Loading & Unloading").description,
    val draftRequirements: String = getCategorySuggestion("Loading & Unloading").requirements,
    val isDescriptionUserEdited: Boolean = false,
    val isRequirementsUserEdited: Boolean = false,
    val draftPayStructure: List<DurationPay> = emptyList(),
    val pricingOptions: List<DurationPay> = emptyList(),
    val pricingQuote: Map<String, String> = emptyMap(),
    val lastPostedJob: JobPost? = null,
    val isLoading: Boolean = false,
    val errorMessage: String? = null
)

class ShopkeeperViewModel : ViewModel() {
    private val _uiState = MutableStateFlow(ShopkeeperState())
    val uiState: StateFlow<ShopkeeperState> = _uiState.asStateFlow()

    fun setError(message: String) {
        _uiState.update { it.copy(errorMessage = message, pricingQuote = emptyMap()) }
    }

    fun updateTitle(title: String) {
        _uiState.update { it.copy(draftTitle = title) }
    }

    fun updateCategory(category: String) {
        val isDelivery = category.contains("Delivery", ignoreCase = true)
        val suggestion = getCategorySuggestion(category)
        _uiState.update { currentState ->
            val newDescription = if (!currentState.isDescriptionUserEdited) suggestion.description else currentState.draftDescription
            val newRequirements = if (!currentState.isRequirementsUserEdited) suggestion.requirements else currentState.draftRequirements
            currentState.copy(
                draftCategory = category,
                draftTitle = category,
                draftIsDelivery = isDelivery,
                draftDescription = newDescription,
                draftRequirements = newRequirements,
                pricingQuote = emptyMap()
            )
        }
    }

    fun updateLocation(location: String) {
        _uiState.update { it.copy(draftLocation = location, pricingQuote = emptyMap()) }
    }

    fun updatePickupLocation(pickup: String) {
        _uiState.update { it.copy(draftPickupLocation = pickup, pricingQuote = emptyMap()) }
    }

    fun updateDropLocation(drop: String) {
        _uiState.update { it.copy(draftDropLocation = drop, pricingQuote = emptyMap()) }
    }

    fun updatePackageType(packageType: String) {
        _uiState.update { it.copy(draftPackageType = packageType) }
    }

    fun updateWorkerCount(count: Int) {
        _uiState.update { it.copy(draftWorkerCount = maxOf(1, count)) }
    }

    fun updateScheduledDate(date: String) {
        _uiState.update { it.copy(draftScheduledDate = date, pricingQuote = emptyMap()) }
    }

    fun updateScheduledTime(time: String) {
        _uiState.update { it.copy(draftScheduledTime = time, pricingQuote = emptyMap()) }
    }

    fun updateWorkingRequirementType(type: String) {
        val isImmediate = type == "IMMEDIATE"
        _uiState.update { currentState ->
            currentState.copy(
                draftWorkingRequirementType = if (isImmediate) "IMMEDIATE" else "DYNAMIC_TIME",
                draftScheduledTime = if (isImmediate) "Immediate" else (if (currentState.draftScheduledTime == "Immediate") "09:00 AM" else currentState.draftScheduledTime),
                pricingQuote = emptyMap()
            )
        }
    }

    fun updateBookingType(type: String) {
        val isCurrent = type == "CURRENT"
        _uiState.update { currentState ->
            currentState.copy(
                draftBookingType = if (isCurrent) "CURRENT" else "PRE_BOOKING",
                draftScheduledDate = if (isCurrent) todayIsoDate() else "",
                draftWorkingRequirementType = if (isCurrent) "IMMEDIATE" else "DYNAMIC_TIME",
                draftScheduledTime = if (isCurrent) "Immediate" else "",
                pricingQuote = emptyMap()
            )
        }
    }

    fun updateDescription(description: String) {
        _uiState.update {
            it.copy(
                draftDescription = description,
                isDescriptionUserEdited = true
            )
        }
    }

    fun updateRequirements(requirements: String) {
        _uiState.update {
            it.copy(
                draftRequirements = requirements,
                isRequirementsUserEdited = true
            )
        }
    }

    fun applyCategorySuggestions() {
        _uiState.update { currentState ->
            val suggestion = getCategorySuggestion(currentState.draftCategory)
            currentState.copy(
                draftDescription = suggestion.description,
                draftRequirements = suggestion.requirements,
                isDescriptionUserEdited = false,
                isRequirementsUserEdited = false
            )
        }
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
        val initialCategory = "Loading & Unloading"
        val initialSuggestion = getCategorySuggestion(initialCategory)
        _uiState.update {
            it.copy(
                draftTitle = initialCategory,
                draftCategory = initialCategory,
                draftLocation = "Okhla Market Area",
                draftPickupLocation = "Okhla Market Store #12",
                draftDropLocation = "Sector 18 Noida",
                draftPackageType = "Parcel / Product Box",
                draftIsDelivery = false,
                draftWorkerCount = 1,
                draftScheduledDate = todayIsoDate(),
                draftBookingType = "CURRENT",
                draftWorkingRequirementType = "IMMEDIATE",
                draftScheduledTime = "Immediate",
                draftSubmitted = false,
                draftDescription = initialSuggestion.description,
                draftRequirements = initialSuggestion.requirements,
                isDescriptionUserEdited = false,
                isRequirementsUserEdited = false,
                draftPayStructure = emptyList(),
                pricingQuote = emptyMap(),
                errorMessage = null
            )
        }
    }

    fun toggleDurationPay(hours: Int, defaultPrice: Int) {
        _uiState.update { state ->
            val configured = state.pricingOptions.firstOrNull { it.hours == hours } ?: return@update state
            state.copy(draftPayStructure = listOf(configured), pricingQuote = emptyMap())
        }
    }

    fun removeDurationPay(item: DurationPay) {
        _uiState.update { state ->
            state.copy(draftPayStructure = state.draftPayStructure.filter { dp -> dp.hours != item.hours }, pricingQuote = emptyMap())
        }
    }

    fun updatePrice(hours: Int, newPrice: Int) {
        // Prices and limits are authoritative backend values and are never edited on the client.
    }

    fun addDurationPay(hours: Int, price: Int) {
        _uiState.update { state ->
            val configured = state.pricingOptions.firstOrNull { it.hours == hours } ?: return@update state
            state.copy(draftPayStructure = listOf(configured), pricingQuote = emptyMap())
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
        try {
            val profile = ErrnoMobileApi.profile()
            val shop = ErrnoMobileApi.shop()
            _uiState.update { it.copy(ownerName = profile.optString("name", "Shopkeeper"), shopName = shop?.optString("shop_name", "My Store") ?: "My Store", shopAddress = shop?.optString("address", "") ?: "", errorMessage = null) }
        } catch (error: Exception) {
            _uiState.update { it.copy(errorMessage = error.localizedMessage ?: "Unable to load profile.") }
        }
    }

    suspend fun refreshPricing() {
        try {
            val configured = ErrnoMobileApi.pricingDurations()
            _uiState.update { state ->
                val selected = configured.firstOrNull { it.hours == state.draftPayStructure.firstOrNull()?.hours } ?: configured.firstOrNull()
                state.copy(pricingOptions = configured, draftPayStructure = listOfNotNull(selected), pricingQuote = emptyMap(), errorMessage = null)
            }
        } catch (error: Exception) {
            _uiState.update { it.copy(errorMessage = error.localizedMessage ?: "Pricing configuration is unavailable.") }
        }
    }

    suspend fun saveProfile(name: String, storeName: String) {
        val current = _uiState.value
        val profile = ErrnoMobileApi.updateProfile(name.trim())
        val shop = ErrnoMobileApi.saveShop(storeName.trim(), current.shopAddress, "General Store")
        _uiState.update { it.copy(ownerName = profile.optString("name"), shopName = shop.optString("shop_name"), errorMessage = null) }
    }

    suspend fun refreshQuote() {
        val state = _uiState.value
        val hours = state.draftPayStructure.firstOrNull()?.hours ?: error("Select a configured duration first.")
        val area = if (state.draftIsDelivery) state.draftPickupLocation.ifBlank { "Pickup Store" } else state.draftLocation.ifBlank { "Okhla Market Area" }
        val date = runCatching { java.time.LocalDate.parse(state.draftScheduledDate) }
            .getOrElse { error("Choose a valid service date before requesting a quote.") }
        val time = if (state.draftWorkingRequirementType == "IMMEDIATE") {
            java.time.LocalTime.now()
        } else {
            runCatching { java.time.LocalTime.parse(state.draftScheduledTime, java.time.format.DateTimeFormatter.ofPattern("hh:mm a", Locale.ENGLISH)) }
                .getOrElse { error("Choose a valid service time before requesting a quote.") }
        }
        val quoteSchedule = java.time.LocalDateTime.of(date, time)
            .format(java.time.format.DateTimeFormatter.ofPattern("dd MMM yyyy 'at' hh:mm a", Locale.ENGLISH))
        val quote = ErrnoMobileApi.requestPricingQuote(hours, quoteSchedule, area)
        val fields = listOf("quote_id", "service_start_at", "final_service_charge", "base_price", "maximum_price", "time_multiplier", "demand_multiplier", "commission_amount", "worker_payout_amount", "expires_at")
        _uiState.update { it.copy(pricingQuote = fields.associateWith { key -> quote.optString(key) }.filterValues(String::isNotBlank), errorMessage = null) }
    }

    suspend fun postJob(): JobPost {
        val state = _uiState.value
        check(!state.draftSubmitted) { "This job has already been submitted." }
        val dateFormat = SimpleDateFormat("yyyy-MM-dd", Locale.ROOT).apply { isLenient = false }
        val persistedDate: String
        val persistedTime: String
        if (state.draftBookingType == "CURRENT") {
            persistedDate = todayIsoDate()
            persistedTime = if (state.draftWorkingRequirementType == "IMMEDIATE") "Immediate" else state.draftScheduledTime
        } else {
            require(state.draftBookingType == "PRE_BOOKING" && state.draftScheduledDate.isNotBlank()) { "Choose a valid pre-booking date." }
            val pos = ParsePosition(0)
            val parsed = dateFormat.parse(state.draftScheduledDate, pos)?.takeIf { pos.index == state.draftScheduledDate.length && pos.errorIndex < 0 }
                ?: error("Choose a valid pre-booking date.")
            val today = Calendar.getInstance().apply { set(Calendar.HOUR_OF_DAY, 0); set(Calendar.MINUTE, 0); set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0) }
            val selected = Calendar.getInstance().apply { time = parsed; set(Calendar.HOUR_OF_DAY, 0); set(Calendar.MINUTE, 0); set(Calendar.SECOND, 0); set(Calendar.MILLISECOND, 0) }
            val first = (today.clone() as Calendar).apply { add(Calendar.DAY_OF_YEAR, 1) }
            val last = (today.clone() as Calendar).apply { add(Calendar.DAY_OF_YEAR, 7) }
            require(!selected.before(first) && !selected.after(last)) { "Pre-booking must be scheduled within the next seven days." }
            require(state.draftWorkingRequirementType != "DYNAMIC_TIME" || (state.draftScheduledTime.isNotBlank() && state.draftScheduledTime != "Immediate")) { "Choose a start time for the pre-booking." }
            persistedDate = dateFormat.format(selected.time)
            persistedTime = if (state.draftWorkingRequirementType == "IMMEDIATE") "Immediate" else state.draftScheduledTime
        }
        val quoteId = state.pricingQuote["quote_id"] ?: error("Request a current price quote before confirming the job.")
        val serviceStart = state.pricingQuote["service_start_at"] ?: error("The pricing quote has no service time.")
        val expiry = state.pricingQuote["expires_at"] ?: error("The pricing quote has no expiry.")
        val expiryMillis = runCatching { java.time.Instant.parse(expiry).toEpochMilli() }.getOrElse { error("The pricing quote expiry is invalid.") }
        require(expiryMillis > System.currentTimeMillis()) { "The price quote has expired. Request a new quote." }
        val chosen = state.draftPayStructure.firstOrNull() ?: error("Select a configured duration.")
        require(state.pricingOptions.any { it.hours == chosen.hours && it.price == chosen.price }) { "Selected price is no longer configured. Refresh pricing." }
        val suggestion = getCategorySuggestion(state.draftCategory)
        val location = if (state.draftIsDelivery) "${state.draftPickupLocation.ifBlank { "Pickup Store" }} -> ${state.draftDropLocation.ifBlank { "Drop Address" }}" else state.draftLocation.ifBlank { "Okhla Market Area" }
        val draft = JobPost(
            id = System.currentTimeMillis().toString(), title = state.draftCategory.ifBlank { "Loading & Unloading" },
            category = state.draftCategory.ifBlank { "Loading & Unloading" }, location = location,
            description = state.draftDescription.ifBlank { suggestion.description },
            requirements = state.draftRequirements.ifBlank { suggestion.requirements }, payStructure = listOf(chosen),
            status = "Active", isDeliveryJob = state.draftIsDelivery,
            pickupLocation = state.draftPickupLocation, dropLocation = state.draftDropLocation,
            packageType = state.draftPackageType, workerCount = state.draftWorkerCount,
            scheduledDate = persistedDate, bookingType = state.draftBookingType,
            workingRequirementType = state.draftWorkingRequirementType, scheduledTime = persistedTime
        )
        _uiState.update { it.copy(isLoading = true, errorMessage = null) }
        try {
            val persisted = ErrnoMobileApi.postJob(draft, quoteId, serviceStart)
            _uiState.update { it.copy(recentJobs = listOf(persisted) + it.recentJobs, activeJobsCount = it.activeJobsCount + 1, lastPostedJob = persisted, draftSubmitted = true, isLoading = false, pricingQuote = emptyMap(), errorMessage = null) }
            return persisted
        } catch (error: Exception) {
            _uiState.update { it.copy(isLoading = false, errorMessage = error.localizedMessage ?: "Unable to post job.") }
            throw error
        }
    }
}
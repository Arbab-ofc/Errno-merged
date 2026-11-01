package com.erno.app.ui.screens.shopkeeper

import androidx.lifecycle.ViewModel
import com.erno.app.data.model.DurationPay
import com.erno.app.data.model.JobPost
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
    val draftPayStructure: List<DurationPay> = listOf(DurationPay(2, 249)),
    val lastPostedJob: JobPost? = null
)

class ShopkeeperViewModel : ViewModel() {
    private val _uiState = MutableStateFlow(ShopkeeperState())
    val uiState: StateFlow<ShopkeeperState> = _uiState.asStateFlow()

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
                draftRequirements = newRequirements
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

    fun updateWorkerCount(count: Int) {
        _uiState.update { it.copy(draftWorkerCount = maxOf(1, count)) }
    }

    fun updateScheduledDate(date: String) {
        _uiState.update { it.copy(draftScheduledDate = date) }
    }

    fun updateScheduledTime(time: String) {
        _uiState.update { it.copy(draftScheduledTime = time) }
    }

    fun updateWorkingRequirementType(type: String) {
        val isImmediate = type == "IMMEDIATE"
        _uiState.update { currentState ->
            currentState.copy(
                draftWorkingRequirementType = if (isImmediate) "IMMEDIATE" else "DYNAMIC_TIME",
                draftScheduledTime = if (isImmediate) "Immediate" else (if (currentState.draftScheduledTime == "Immediate") "09:00 AM" else currentState.draftScheduledTime)
            )
        }
    }

    fun updateBookingType(type: String) {
        val isCurrent = type == "CURRENT"
        _uiState.update { currentState ->
            currentState.copy(
                draftBookingType = if (isCurrent) "CURRENT" else "PRE_BOOKING",
                draftScheduledDate = if (isCurrent) todayIsoDate() else "",
                draftScheduledTime = if (currentState.draftWorkingRequirementType == "IMMEDIATE") "Immediate" else currentState.draftScheduledTime
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
            state.copy(draftPayStructure = state.draftPayStructure.filter { dp -> dp.hours != item.hours })
        }
    }

    fun updatePrice(hours: Int, newPrice: Int) {
        _uiState.update { state ->
            val updated = state.draftPayStructure.map {
                if (it.hours == hours) it.copy(price = newPrice) else it
            }
            state.copy(draftPayStructure = updated)
        }
    }

    fun addDurationPay(hours: Int, price: Int) {
        _uiState.update { state ->
            state.copy(draftPayStructure = listOf(DurationPay(hours, price)))
        }
    }

    fun postJob(): JobPost? {
        val state = _uiState.value
        if (state.draftSubmitted) return null

        val todayCal = Calendar.getInstance().apply {
            set(Calendar.HOUR_OF_DAY, 0)
            set(Calendar.MINUTE, 0)
            set(Calendar.SECOND, 0)
            set(Calendar.MILLISECOND, 0)
        }
        val dateFormat = SimpleDateFormat("yyyy-MM-dd", Locale.ROOT).apply { isLenient = false }

        val persistedDate: String
        val persistedTime: String

        if (state.draftBookingType == "CURRENT") {
            // Current Job MUST be assigned today's local date automatically.
            persistedDate = todayIsoDate()
            persistedTime = if (state.draftWorkingRequirementType == "IMMEDIATE") "Immediate" else state.draftScheduledTime.ifBlank { "Immediate" }
        } else if (state.draftBookingType == "PRE_BOOKING") {
            if (state.draftScheduledDate.isBlank()) return null
            if (state.draftWorkingRequirementType == "DYNAMIC_TIME" && (state.draftScheduledTime.isBlank() || state.draftScheduledTime == "Immediate")) return null

            val parsePosition = ParsePosition(0)
            val parsedDate = dateFormat.parse(state.draftScheduledDate, parsePosition)
                ?.takeIf { parsePosition.index == state.draftScheduledDate.length && parsePosition.errorIndex < 0 }
                ?: return null

            val selectedCal = Calendar.getInstance().apply {
                time = parsedDate
                set(Calendar.HOUR_OF_DAY, 0)
                set(Calendar.MINUTE, 0)
                set(Calendar.SECOND, 0)
                set(Calendar.MILLISECOND, 0)
            }

            val firstAllowed = (todayCal.clone() as Calendar).apply { add(Calendar.DAY_OF_YEAR, 1) }
            val lastAllowed = (todayCal.clone() as Calendar).apply { add(Calendar.DAY_OF_YEAR, 7) }

            // Strictly check date boundary: must be between tomorrow and day + 7
            if (selectedCal.before(firstAllowed) || selectedCal.after(lastAllowed)) {
                return null
            }
            persistedDate = dateFormat.format(selectedCal.time)
            persistedTime = if (state.draftWorkingRequirementType == "IMMEDIATE") "Immediate" else state.draftScheduledTime
        } else {
            return null
        }

        val computedLocation = if (state.draftIsDelivery) {
            "${state.draftPickupLocation.ifBlank { "Pickup Store" }} -> ${state.draftDropLocation.ifBlank { "Drop Address" }}"
        } else {
            state.draftLocation.ifBlank { "Okhla Market Area" }
        }

        val categorySuggestion = getCategorySuggestion(state.draftCategory)

        val newJob = JobPost(
            id = System.currentTimeMillis().toString(),
            title = state.draftCategory.ifBlank { "Loading & Unloading" },
            category = state.draftCategory.ifBlank { "Loading & Unloading" },
            location = computedLocation,
            description = state.draftDescription.ifBlank { categorySuggestion.description },
            requirements = state.draftRequirements.ifBlank { categorySuggestion.requirements },
            payStructure = if (state.draftPayStructure.isNotEmpty()) state.draftPayStructure else listOf(DurationPay(2, 249)),
            status = "Active",
            postedTime = "Posted just now",
            applicantsCount = 0,
            isDeliveryJob = state.draftIsDelivery,
            pickupLocation = state.draftPickupLocation,
            dropLocation = state.draftDropLocation,
            packageType = state.draftPackageType,
            workerCount = state.draftWorkerCount,
            scheduledDate = persistedDate,
            bookingType = state.draftBookingType,
            workingRequirementType = state.draftWorkingRequirementType,
            scheduledTime = persistedTime
        )

        _uiState.update {
            it.copy(
                recentJobs = listOf(newJob) + it.recentJobs,
                activeJobsCount = it.activeJobsCount + 1,
                lastPostedJob = newJob,
                draftSubmitted = true
            )
        }
        return newJob
    }
}

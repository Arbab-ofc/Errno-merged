package com.erno.app.data.model

data class DurationPay(
    val hours: Int,
    val price: Int
)

data class JobPost(
    val id: String,
    val title: String,
    val category: String,
    val location: String,
    val description: String,
    val payStructure: List<DurationPay>,
    val status: String = "Active", // "Active", "Worker Assigned", "Completed"
    val postedTime: String = "Just now",
    val applicantsCount: Int = 0,
    val isDeliveryJob: Boolean = false,
    val pickupLocation: String = "Shop / Store Location",
    val dropLocation: String = "Customer Address / Target Location",
    val packageType: String = "Standard Package",
    val scheduledDate: String = "Today",
    val workerRating: Float = 0f,
    val shopkeeperRating: Float = 0f,
    val reviewComment: String = "",
    val assignedWorkerName: String = "",
    val assignedWorkerPhone: String = "+919876543210",
    val assignedWorkerRating: Float = 4.8f,
    val assignedWorkerShiftsCount: Int = 14,
    val isWorkerAssigned: Boolean = false
)

data class WorkerJob(
    val id: String,
    val title: String,
    val location: String,
    val distance: String,
    val description: String,
    val payStructure: List<DurationPay>,
    val isNew: Boolean = false,
    val selectedHours: Int = 2,
    val selectedPay: Int = 189,
    val status: String = "Available", // "Available", "Accepting", "Accepted", "Upcoming", "Ongoing", "Completed"
    val scheduledTime: String = "Today, 11:00 AM",
    val latitude: Double = 28.5355,
    val longitude: Double = 77.2641,
    val isDeliveryJob: Boolean = false,
    val pickupLocation: String = "Okhla Shop Store",
    val dropLocation: String = "Sector 15 Noida",
    val packageType: String = "Grocery / Parcel Delivery",
    val scheduledDate: String = "Today",
    val workerRating: Float = 0f,
    val shopkeeperRating: Float = 0f,
    val reviewComment: String = ""
)

data class WorkerApplication(
    val id: String,
    val jobId: String,
    val status: String,
    val createdAt: String,
    val jobTitle: String,
    val jobStatus: String,
    val location: String,
    val scheduledDate: String,
    val payAmount: Int,
    val shopName: String,
    val shopAddress: String
)

data class EarningRecord(
    val id: String,
    val jobTitle: String,
    val hours: String,
    val date: String,
    val amount: Int
)

package com.erno.app.data.repository

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow

data class PaymentUiStatus(val bookingId: String? = null, val status: String? = null, val message: String? = null)

object PaymentUiState {
    private val mutable = MutableStateFlow(PaymentUiStatus())
    val state = mutable.asStateFlow()
    fun update(value: PaymentUiStatus) { mutable.value = value }
}

package com.erno.app.data.repository

import org.junit.Assert.assertEquals
import org.junit.Test

class PaymentUiStateTest {
    @Test
    fun paymentStatusReflectsBackendConfirmedStateOnly() {
        PaymentUiState.update(PaymentUiStatus())
        PaymentUiState.update(PaymentUiStatus(bookingId = "booking-1", status = "PAYMENT_PROCESSING"))
        assertEquals("PAYMENT_PROCESSING", PaymentUiState.state.value.status)
        PaymentUiState.update(PaymentUiStatus(bookingId = "booking-1", status = "PAID"))
        assertEquals("PAID", PaymentUiState.state.value.status)
        PaymentUiState.update(PaymentUiStatus())
    }
}

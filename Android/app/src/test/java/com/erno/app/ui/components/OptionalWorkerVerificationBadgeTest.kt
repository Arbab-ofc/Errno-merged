package com.erno.app.ui.components

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class OptionalWorkerVerificationBadgeTest {
    @Test
    fun missingOrBlankKycStatusDoesNotProduceAVerifiedBadge() {
        assertNull(workerVerificationBadgeLabel(null))
        assertNull(workerVerificationBadgeLabel("  "))
        assertNull(workerVerificationBadgeLabel("NOT_STARTED"))
    }

    @Test
    fun explicitVerifiedLabelCanBeDisplayed() {
        assertEquals("Aadhaar Verified", workerVerificationBadgeLabel("Aadhaar Verified"))
    }
}

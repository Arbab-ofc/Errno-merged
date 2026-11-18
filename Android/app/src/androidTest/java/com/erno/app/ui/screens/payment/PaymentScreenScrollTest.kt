package com.erno.app.ui.screens.payment

import androidx.compose.material3.Text
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performScrollTo
import org.junit.Rule
import org.junit.Test

class PaymentScreenScrollTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun paymentActionsRemainReachableBelowScreenshotPreview() {
        composeRule.setContent {
            PaymentScreenScrollColumn {
                Text("UPI payment")
                Text("Booking and payable amount")
                Text("ERRNO UPI payment QR")
                Text("Payee and UPI ID")
                Text("Selected payment screenshot preview")
                Text("Replace screenshot")
                Text("Submit for Verification")
                Text("Refresh payment status")
            }
        }

        composeRule.onNodeWithText("Submit for Verification").performScrollTo().assertIsDisplayed()
        composeRule.onNodeWithText("Refresh payment status").performScrollTo().assertIsDisplayed()
    }
}

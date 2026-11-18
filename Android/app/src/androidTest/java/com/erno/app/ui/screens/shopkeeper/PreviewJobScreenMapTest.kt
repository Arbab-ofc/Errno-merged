package com.erno.app.ui.screens.shopkeeper

import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onAllNodesWithText
import org.junit.Assert.assertEquals
import org.junit.Rule
import org.junit.Test

class PreviewJobScreenMapTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun previewUsesSelectedShopCoordinatesInsteadOfAddressFallback() {
        composeRule.setContent {
            PreviewJobScreen(
                state = ShopkeeperState(
                    draftLocation = "Okhla Market, New Delhi",
                    draftLatitude = 28.6139,
                    draftLongitude = 77.2090,
                ),
                onBackClick = {},
                onEditClick = {},
                onPostJobClick = {},
            )
        }

        val addressFallbackNodes = composeRule.onAllNodesWithText(
            "Shop coordinates are unavailable. Use the saved address.",
            useUnmergedTree = true,
        ).fetchSemanticsNodes()
        assertEquals("Preview should use the selected map coordinates", 0, addressFallbackNodes.size)
    }
}

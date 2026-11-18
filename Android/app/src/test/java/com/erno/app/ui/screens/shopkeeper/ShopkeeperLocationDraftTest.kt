package com.erno.app.ui.screens.shopkeeper

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

class ShopkeeperLocationDraftTest {
    @Test
    fun resolvedAddressAndCoordinatesReachTheJobDraft() {
        val viewModel = ShopkeeperViewModel()

        viewModel.updateMapLocation("Okhla Market, New Delhi", 28.5355, 77.2732)

        val draft = viewModel.uiState.value
        assertEquals("Okhla Market, New Delhi", draft.draftLocation)
        assertEquals(28.5355, draft.draftLatitude!!, 0.000001)
        assertEquals(77.2732, draft.draftLongitude!!, 0.000001)
    }

    @Test
    fun editingResolvedAddressClearsCoordinatesToAvoidStaleJobLocation() {
        val viewModel = ShopkeeperViewModel()
        viewModel.updateMapLocation("Okhla Market, New Delhi", 28.5355, 77.2732)

        viewModel.updateLocation("A different address")

        assertEquals("A different address", viewModel.uiState.value.draftLocation)
        assertNull(viewModel.uiState.value.draftLatitude)
        assertNull(viewModel.uiState.value.draftLongitude)
    }

    @Test
    fun resolvedDeliveryPickupAddressAndCoordinatesReachTheJobDraft() {
        val viewModel = ShopkeeperViewModel()

        viewModel.updatePickupMapLocation("Okhla Market, New Delhi", 28.5355, 77.2732)

        val draft = viewModel.uiState.value
        assertEquals("Okhla Market, New Delhi", draft.draftPickupLocation)
        assertEquals(28.5355, draft.draftLatitude!!, 0.000001)
        assertEquals(77.2732, draft.draftLongitude!!, 0.000001)
    }
}

package com.erno.app.ui.screens.shopkeeper

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class JobLocationCoordinatesTest {
    @Test
    fun jobRequiresACompleteFiniteInRangeCoordinatePair() {
        assertTrue(hasValidJobCoordinates(28.6139, 77.2090))
        assertFalse(hasValidJobCoordinates(null, null))
        assertFalse(hasValidJobCoordinates(28.6139, null))
        assertFalse(hasValidJobCoordinates(Double.NaN, 77.2090))
        assertFalse(hasValidJobCoordinates(91.0, 77.2090))
        assertFalse(hasValidJobCoordinates(28.6139, 181.0))
    }
}

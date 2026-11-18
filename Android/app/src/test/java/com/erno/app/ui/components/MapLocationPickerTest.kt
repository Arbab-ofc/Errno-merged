package com.erno.app.ui.components

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class MapLocationPickerTest {
    @Test
    fun acceptsValidCoordinatesIncludingBounds() {
        assertTrue(isCoordinate(28.6139, 77.2090))
        assertTrue(isCoordinate(-90.0, -180.0))
        assertTrue(isCoordinate(90.0, 180.0))
    }

    @Test
    fun rejectsMissingNonFiniteAndOutOfRangeCoordinates() {
        assertFalse(isCoordinate(null, 77.2090))
        assertFalse(isCoordinate(28.6139, null))
        assertFalse(isCoordinate(Double.NaN, 77.2090))
        assertFalse(isCoordinate(28.6139, Double.POSITIVE_INFINITY))
        assertFalse(isCoordinate(-90.0001, 0.0))
        assertFalse(isCoordinate(0.0, 180.0001))
    }
}

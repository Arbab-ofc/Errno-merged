package com.erno.app.ui.components

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class PhotonGeocodingTest {
    @Test
    fun parsesPhotonLongitudeLatitudeInCorrectOrder() {
        val result = parsePhotonResults(
            """{"features":[{"geometry":{"coordinates":[77.209,28.6139]},"properties":{"name":"Okhla Market","city":"New Delhi"}}]}""",
        ).single()

        assertEquals("Okhla Market, New Delhi", result.label)
        assertEquals(28.6139, result.latitude, 0.000001)
        assertEquals(77.209, result.longitude, 0.000001)
    }

    @Test
    fun ignoresMalformedMissingAndOutOfRangePhotonCoordinates() {
        assertTrue(parsePhotonResults("not-json").isEmpty())
        assertTrue(parsePhotonResults("""{"features":[]}""").isEmpty())
        assertTrue(
            parsePhotonResults(
                """{"features":[
                    {"geometry":{"coordinates":[77.2]},"properties":{"name":"Missing latitude"}},
                    {"geometry":{"coordinates":[999,28.6]},"properties":{"name":"Invalid longitude"}},
                    {"geometry":{"coordinates":[77.2,91]},"properties":{"name":"Invalid latitude"}}
                ]}""",
            ).isEmpty(),
        )
    }
}

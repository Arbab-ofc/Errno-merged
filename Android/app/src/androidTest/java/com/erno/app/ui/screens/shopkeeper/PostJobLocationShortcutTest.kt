package com.erno.app.ui.screens.shopkeeper

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithText
import androidx.compose.ui.test.performClick
import com.erno.app.data.model.MapCoordinate
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Rule
import org.junit.Test

class PostJobLocationShortcutTest {
    @get:Rule
    val composeRule = createComposeRule()

    @Test
    fun allPopularShortcutsResolveAndPropagateTheirCoordinates() {
        val expected = listOf(
            "Okhla Market" to "Okhla Market, Okhla, New Delhi, India",
            "Sector 18 Noida" to "Sector 18 Market, Noida, Uttar Pradesh, India",
            "Lajpat Nagar" to "Lajpat Nagar Market, New Delhi, India",
            "Connaught Place" to "Connaught Place, New Delhi, India",
        )
        val selected = mutableStateListOf<Triple<String, Double, Double>>()

        composeRule.setContent {
            val address = remember { mutableStateOf("") }
            Column(Modifier.verticalScroll(rememberScrollState())) {
                SimpleBeginnerLocationInput(
                    value = address.value,
                    onValueChange = { address.value = it },
                    label = "Shop / Work Address",
                    placeholder = "Enter an address",
                    onLocationResolved = { addressText, lat, lng -> selected.add(Triple(addressText, lat, lng)) },
                    geocodeAddress = { query ->
                        val index = expected.indexOfFirst { it.second == query }
                        if (index < 0) null else MapCoordinate(28.6 + index / 100.0, 77.2 + index / 100.0)
                    },
                )
            }
        }

        expected.forEachIndexed { index, (button, expectedAddress) ->
            composeRule.onNodeWithText(button).performClick()
            composeRule.waitUntil(5_000) { selected.size > index }
            val actual = selected[index]
            assertEquals(expectedAddress, actual.first)
            assertEquals(28.6 + index / 100.0, actual.second, 0.000001)
            assertEquals(77.2 + index / 100.0, actual.third, 0.000001)
        }
    }

    @Test
    fun okhlaAddressShortcutResolvesThroughTheSelectedCoordinatesCallback() {
        val selected = mutableStateOf<Triple<String, Double, Double>?>(null)
        composeRule.setContent {
            val address = remember { mutableStateOf("") }
            SimpleBeginnerLocationInput(
                value = address.value,
                onValueChange = { address.value = it },
                label = "Shop / Work Address",
                placeholder = "Enter an address",
                onLocationResolved = { text, lat, lng -> selected.value = Triple(text, lat, lng) },
                geocodeAddress = { MapCoordinate(28.5355, 77.2732) },
            )
        }

        composeRule.onNodeWithText("Use Okhla Market address").performClick()
        composeRule.waitUntil(5_000) { selected.value != null }
        assertEquals("Okhla Main Market, Okhla, New Delhi, India", selected.value?.first)
        assertEquals(28.5355, selected.value?.second ?: 0.0, 0.000001)
        assertEquals(77.2732, selected.value?.third ?: 0.0, 0.000001)
    }

    @Test
    fun invalidGeocodingResponseDoesNotEmitCoordinatesAndShowsManualPinFallback() {
        val selected = mutableStateOf(false)
        composeRule.setContent {
            val address = remember { mutableStateOf("") }
            SimpleBeginnerLocationInput(
                value = address.value,
                onValueChange = { address.value = it },
                label = "Shop / Work Address",
                placeholder = "Enter an address",
                onLocationResolved = { _, _, _ -> selected.value = true },
                geocodeAddress = { MapCoordinate(91.0, 77.2) },
            )
        }

        composeRule.onNodeWithText("Okhla Market").performClick()
        composeRule.onNodeWithText("No valid map coordinates found. Choose the location pin manually.")
            .assertIsDisplayed()
        assertFalse(selected.value)
    }
}

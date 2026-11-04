import java.util.Properties

plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.compose)
    id("com.google.gms.google-services")
}

android {
    namespace = "com.erno.app"
    compileSdk = 36

    defaultConfig {
        applicationId = "com.erno.app"
        minSdk = 24
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"
        val localApiProperties = Properties().apply {
            rootProject.file("gradle.properties.local").takeIf { it.isFile }?.inputStream()?.use { load(it) }
        }
        val apiBaseUrl = providers.gradleProperty("ERRNO_API_BASE_URL")
            .getOrElse(localApiProperties.getProperty("ERRNO_API_BASE_URL") ?: "")
        val photonEndpoint = localApiProperties.getProperty("ERRNO_PHOTON_ENDPOINT") ?: providers.gradleProperty("ERRNO_PHOTON_ENDPOINT").orElse("https://photon.komoot.io").get()
        val osrmEndpoint = localApiProperties.getProperty("ERRNO_OSRM_ENDPOINT") ?: providers.gradleProperty("ERRNO_OSRM_ENDPOINT").orElse("https://router.project-osrm.org/route/v1/driving").get()
        val tileEndpoint = localApiProperties.getProperty("ERRNO_TILE_ENDPOINT") ?: providers.gradleProperty("ERRNO_TILE_ENDPOINT").orElse("https://tiles.openfreemap.org/planet").get()
        val mapStyleUrl = localApiProperties.getProperty("ERRNO_MAP_STYLE_URL") ?: providers.gradleProperty("ERRNO_MAP_STYLE_URL").orElse("https://tiles.openfreemap.org/styles/liberty").get()
        val authEmulatorHost = providers.gradleProperty("ERRNO_FIREBASE_AUTH_EMULATOR_HOST")
            .getOrElse(localApiProperties.getProperty("ERRNO_FIREBASE_AUTH_EMULATOR_HOST") ?: "")
        buildConfigField("String", "ERRNO_API_BASE_URL", "\"$apiBaseUrl\"")
        buildConfigField("String", "ERRNO_PHOTON_ENDPOINT", "\"$photonEndpoint\"")
        buildConfigField("String", "ERRNO_OSRM_ENDPOINT", "\"$osrmEndpoint\"")
        buildConfigField("String", "ERRNO_TILE_ENDPOINT", "\"$tileEndpoint\"")
        buildConfigField("String", "ERRNO_MAP_STYLE_URL", "\"$mapStyleUrl\"")
        buildConfigField("String", "ERRNO_FIREBASE_AUTH_EMULATOR_HOST", "\"$authEmulatorHost\"")

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
    kotlinOptions {
        jvmTarget = "11"
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
}

dependencies {

    implementation("com.razorpay:checkout:1.6.40")
    implementation("io.coil-kt:coil-compose:2.7.0")
    implementation("com.squareup.okhttp3:okhttp:4.12.0")

    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.compose)
    implementation(libs.androidx.navigation.compose)
    implementation(libs.androidx.activity.compose)
    implementation(platform(libs.androidx.compose.bom))
    implementation(libs.androidx.ui)
    implementation(libs.androidx.ui.graphics)
    implementation(libs.androidx.ui.tooling.preview)
    implementation(libs.androidx.material3)
    implementation(libs.androidx.compose.material.icons.extended)
    implementation(platform("com.google.firebase:firebase-bom:34.4.0"))
    implementation("com.google.firebase:firebase-auth")
    implementation("com.google.firebase:firebase-messaging")
    implementation("androidx.credentials:credentials:1.5.0")
    implementation("androidx.credentials:credentials-play-services-auth:1.5.0")
    implementation("com.google.android.libraries.identity.googleid:googleid:1.1.1")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-play-services:1.10.2")
    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
    androidTestImplementation(libs.androidx.espresso.core)
    androidTestImplementation(platform(libs.androidx.compose.bom))
    androidTestImplementation(libs.androidx.ui.test.junit4)
    debugImplementation(libs.androidx.ui.tooling)
    debugImplementation(libs.androidx.ui.test.manifest)
}

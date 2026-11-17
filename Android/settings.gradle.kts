pluginManagement {
    repositories {
        google {
            content {
                includeGroupByRegex("com\\.android.*")
                includeGroupByRegex("com\\.google.*")
                includeGroupByRegex("androidx.*")
            }
        }
        mavenCentral()
        gradlePluginPortal()
    }
}
plugins {
    id("org.gradle.toolchains.foojay-resolver-convention") version "0.10.0"
}
// Synchronize public Android settings before project configuration reads the
// generated gradle.properties.local file. Runs once per Gradle invocation.
val repositoryRoot = settingsDir.parentFile
val environmentSync = providers.exec {
    workingDir(repositoryRoot)
    commandLine("python3", "scripts/sync_native_configs.py", "--sync", "--target", "android")
}
environmentSync.result.get().assertNormalExitValue()

dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}

rootProject.name = "My Application"
include(":app")

package com.erno.app.navigation

import android.app.Activity
import android.widget.Toast
import androidx.credentials.exceptions.GetCredentialCancellationException
import androidx.compose.runtime.*
import androidx.compose.ui.platform.LocalContext
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import com.erno.app.ui.components.ShopkeeperTab
import com.erno.app.ui.components.WorkerTab
import com.erno.app.ui.screens.auth.RegisterScreen
import com.erno.app.ui.screens.auth.VerifyOTPScreen
import com.erno.app.ui.screens.home.HomeScreen
import com.erno.app.ui.screens.role.Role
import com.erno.app.ui.screens.role.RoleSelectionScreen
import com.erno.app.ui.screens.shopkeeper.*
import com.erno.app.ui.screens.worker.*
import androidx.navigation.NavType
import androidx.navigation.navArgument
import com.erno.app.ui.screens.auth.DigiLockerVerificationScreen
import com.erno.app.ui.screens.legal.PrivacyPolicyScreen
import com.erno.app.ui.screens.legal.TermsConditionsScreen
import com.erno.app.ui.screens.legal.TermsConsentScreen
import com.erno.app.data.repository.FirebaseGoogleAuth
import kotlinx.coroutines.launch
import kotlinx.coroutines.CancellationException

private fun NavHostController.navigateTab(rootRoute: String, targetRoute: String) {
    if (currentDestination?.route == targetRoute) return
    navigate(targetRoute) {
        popUpTo(rootRoute) { saveState = true }
        launchSingleTop = true
        restoreState = true
    }
}

@Composable
fun NavGraph(navController: NavHostController) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var googleLoading by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) {
        runCatching { FirebaseGoogleAuth.restore() }.getOrNull()?.let { identity ->
            val route = when (identity.role) {
                "worker" -> Screen.WorkerHome.route
                "shopkeeper", "shop_owner" -> Screen.ShopkeeperHome.route
                else -> Screen.RoleSelection.route
            }
            navController.navigate(route) { popUpTo(Screen.RoleSelection.route) { inclusive = true } }
        }
    }
    fun googleSignIn(selectedRole: String) {
        if (googleLoading) return
        googleLoading = true
        scope.launch {
            try {
                val activity = context as? Activity ?: error("Sign-in is unavailable in this context.")
                val identity = FirebaseGoogleAuth.signIn(activity, selectedRole)
                val route = when (identity.role) {
                    "worker" -> Screen.WorkerHome.route
                    "shopkeeper", "shop_owner" -> Screen.ShopkeeperHome.route
                    else -> Screen.RoleSelection.route
                }
                navController.navigate(route) { popUpTo(Screen.RoleSelection.route) { inclusive = true } }
            } catch (error: Exception) {
                if (error !is CancellationException && error !is GetCredentialCancellationException) {
                    Toast.makeText(context, error.localizedMessage ?: "Google sign-in failed. Please retry.", Toast.LENGTH_LONG).show()
                }
            } finally {
                googleLoading = false
            }
        }
    }
    val shopkeeperViewModel: ShopkeeperViewModel = viewModel()
    val shopkeeperState by shopkeeperViewModel.uiState.collectAsState()

    val workerViewModel: WorkerViewModel = viewModel()
    val workerState by workerViewModel.uiState.collectAsState()

    NavHost(
        navController = navController,
        startDestination = Screen.RoleSelection.route
    ) {
        composable(Screen.RoleSelection.route) {
            RoleSelectionScreen(
                onShopkeeperClick = {
                    navController.navigate(Screen.TermsConsent.createRoute(Screen.ShopkeeperLogin.route))
                },
                onWorkerClick = {
                    navController.navigate(Screen.TermsConsent.createRoute(Screen.WorkerLogin.route))
                },
                onCreateAccount = {
                    navController.navigate(Screen.TermsConsent.createRoute(Screen.Register.route))
                },
                onTermsClick = {
                    navController.navigate(Screen.TermsConditions.route)
                },
                onPrivacyClick = {
                    navController.navigate(Screen.PrivacyPolicy.route)
                }
            )
        }

        composable(
            route = "terms_consent/{targetRoute}",
            arguments = listOf(navArgument("targetRoute") { type = NavType.StringType })
        ) { backStackEntry ->
            val targetRoute = backStackEntry.arguments?.getString("targetRoute") ?: Screen.RoleSelection.route
            TermsConsentScreen(
                onAgreeClick = {
                    navController.navigate(targetRoute) {
                        popUpTo(Screen.RoleSelection.route) { inclusive = false }
                    }
                },
                onTermsClick = {
                    navController.navigate(Screen.TermsConditions.route)
                },
                onPrivacyClick = {
                    navController.navigate(Screen.PrivacyPolicy.route)
                }
            )
        }
        
        composable(Screen.ShopkeeperLogin.route) {
            ShopkeeperLoginScreen(
                onBackClick = {
                    navController.popBackStack()
                },
                onSendOTP = { phoneNumber ->
                    navController.navigate("verify_otp/$phoneNumber?role=shopkeeper")
                },
                onGoogleSignInClick = { googleSignIn("shop_owner") },
                isGoogleLoading = googleLoading,
                onCreateAccount = {
                    navController.navigate(Screen.TermsConsent.createRoute(Screen.Register.route))
                },
                onTermsClick = {
                    navController.navigate(Screen.TermsConditions.route)
                },
                onPrivacyClick = {
                    navController.navigate(Screen.PrivacyPolicy.route)
                }
            )
        }
        
        composable(Screen.WorkerLogin.route) {
            WorkerLoginScreen(
                onBackClick = {
                    navController.popBackStack()
                },
                onSendOTP = { phoneNumber ->
                    navController.navigate("verify_otp/$phoneNumber?role=worker")
                },
                onGoogleSignInClick = { googleSignIn("worker") },
                isGoogleLoading = googleLoading,
                onCreateAccount = {
                    navController.navigate(Screen.TermsConsent.createRoute(Screen.Register.route))
                },
                onTermsClick = {
                    navController.navigate(Screen.TermsConditions.route)
                },
                onPrivacyClick = {
                    navController.navigate(Screen.PrivacyPolicy.route)
                }
            )
        }

        composable(Screen.Register.route) {
            RegisterScreen(
                onBackClick = {
                    navController.popBackStack()
                },
                onRegisterClick = { phoneNumber, role ->
                    val roleParam = if (role == Role.WORKER) "worker" else "shopkeeper"
                    navController.navigate("verify_otp/$phoneNumber?role=$roleParam")
                },
                onLoginClick = {
                    navController.navigate(Screen.RoleSelection.route) {
                        popUpTo(Screen.Register.route) { inclusive = true }
                    }
                },
                onGoogleSignInClick = { role -> googleSignIn(if (role == Role.WORKER) "worker" else "shop_owner") },
                isGoogleLoading = googleLoading
            )
        }

        composable(Screen.PrivacyPolicy.route) {
            PrivacyPolicyScreen(onBackClick = { navController.popBackStack() })
        }

        composable(Screen.TermsConditions.route) {
            TermsConditionsScreen(onBackClick = { navController.popBackStack() })
        }

        composable(
            route = "verify_otp/{phoneNumber}?role={role}",
            arguments = listOf(
                navArgument("phoneNumber") { type = NavType.StringType },
                navArgument("role") {
                    type = NavType.StringType
                    defaultValue = "shopkeeper"
                }
            )
        ) { backStackEntry ->
            val phoneNumber = backStackEntry.arguments?.getString("phoneNumber") ?: ""
            val role = backStackEntry.arguments?.getString("role") ?: "shopkeeper"

            VerifyOTPScreen(
                phoneNumber = phoneNumber,
                onBackClick = {
                    navController.popBackStack()
                },
                onVerifyClick = { otp ->
                    Toast.makeText(context, "Phone OTP is not configured. Use Google sign-in.", Toast.LENGTH_LONG).show()
                    false
                },
                onEditClick = {
                    navController.popBackStack()
                },
                onResendClick = {
                    // Resend logic
                }
            )
        }

        // Shopkeeper Flow Routes
        composable(Screen.ShopkeeperHome.route) {
            LaunchedEffect(Unit) { shopkeeperViewModel.refreshJobs() }
            ShopkeeperDashboardScreen(
                state = shopkeeperState,
                onPostNewJobClick = {
                    shopkeeperViewModel.resetDraft()
                    navController.navigate(Screen.PostJob.route)
                },
                onViewAllClick = {
                    navController.navigate(Screen.ShopkeeperMyJobs.route)
                },
                onNavigateTab = { tab ->
                    when (tab) {
                        ShopkeeperTab.HOME -> navController.navigateTab(Screen.ShopkeeperHome.route, Screen.ShopkeeperHome.route)
                        ShopkeeperTab.JOBS -> navController.navigateTab(Screen.ShopkeeperHome.route, Screen.ShopkeeperMyJobs.route)
                        ShopkeeperTab.APPLICATIONS -> navController.navigateTab(Screen.ShopkeeperHome.route, Screen.ShopkeeperApplications.route)
                        ShopkeeperTab.PROFILE -> navController.navigateTab(Screen.ShopkeeperHome.route, Screen.ShopkeeperProfile.route)
                    }
                }
            )
        }

        composable(Screen.PostJob.route) {
            PostJobScreen(
                state = shopkeeperState,
                onBackClick = {
                    navController.popBackStack()
                },
                onTitleChange = shopkeeperViewModel::updateTitle,
                onCategoryChange = shopkeeperViewModel::updateCategory,
                onLocationChange = shopkeeperViewModel::updateLocation,
                onScheduledDateChange = shopkeeperViewModel::updateScheduledDate,
                onPickupLocationChange = shopkeeperViewModel::updatePickupLocation,
                onDropLocationChange = shopkeeperViewModel::updateDropLocation,
                onPackageTypeChange = shopkeeperViewModel::updatePackageType,
                onDescriptionChange = shopkeeperViewModel::updateDescription,
                onRemoveDuration = shopkeeperViewModel::removeDurationPay,
                onToggleDuration = shopkeeperViewModel::toggleDurationPay,
                onAddMoreDurationClick = {
                    navController.navigate(Screen.PayStructure.route)
                },
                onPreviewJobClick = {
                    navController.navigate(Screen.PreviewJob.route)
                }
            )
        }

        composable(Screen.PayStructure.route) {
            PayStructureScreen(
                state = shopkeeperState,
                onBackClick = {
                    navController.popBackStack()
                },
                onUpdatePrice = shopkeeperViewModel::updatePrice,
                onAddMoreDuration = shopkeeperViewModel::addDurationPay,
                onDoneClick = {
                    navController.popBackStack()
                }
            )
        }

        composable(Screen.PreviewJob.route) {
            PreviewJobScreen(
                state = shopkeeperState,
                onBackClick = {
                    navController.popBackStack()
                },
                onEditClick = {
                    navController.popBackStack()
                },
                onPostJobClick = {
                    scope.launch {
                        try {
                            shopkeeperViewModel.postJob()
                            navController.navigate(Screen.JobSuccess.route) { popUpTo(Screen.ShopkeeperHome.route) }
                        } catch (error: Exception) {
                            Toast.makeText(context, error.localizedMessage ?: "Unable to post job. Retry.", Toast.LENGTH_LONG).show()
                        }
                    }
                }
            )
        }

        composable(Screen.JobSuccess.route) {
            JobSuccessScreen(
                state = shopkeeperState,
                onGoToMyJobsClick = {
                    navController.navigate(Screen.ShopkeeperMyJobs.route) {
                        popUpTo(Screen.ShopkeeperHome.route)
                    }
                },
                onShareJobClick = {
                    // Share job
                }
            )
        }

        composable(Screen.ShopkeeperMyJobs.route) {
            LaunchedEffect(Unit) { shopkeeperViewModel.refreshJobs() }
            ShopkeeperMyJobsScreen(
                state = shopkeeperState,
                onRefresh = { scope.launch { shopkeeperViewModel.refreshJobs() } },
                onBackClick = {
                    navController.popBackStack()
                },
                onRateWorkerClick = shopkeeperViewModel::rateWorker,
                onJobLifecycleAction = { jobId, action -> scope.launch {
                    try { shopkeeperViewModel.updateJobLifecycle(jobId, action) }
                    catch (error: Exception) { Toast.makeText(context, error.localizedMessage ?: "Unable to update job", Toast.LENGTH_LONG).show() }
                } },
                onNavigateTab = { tab ->
                    when (tab) {
                        ShopkeeperTab.HOME -> navController.navigateTab(Screen.ShopkeeperHome.route, Screen.ShopkeeperHome.route)
                        ShopkeeperTab.JOBS -> navController.navigateTab(Screen.ShopkeeperHome.route, Screen.ShopkeeperMyJobs.route)
                        ShopkeeperTab.APPLICATIONS -> navController.navigateTab(Screen.ShopkeeperHome.route, Screen.ShopkeeperApplications.route)
                        ShopkeeperTab.PROFILE -> navController.navigateTab(Screen.ShopkeeperHome.route, Screen.ShopkeeperProfile.route)
                    }
                }
            )
        }

        composable(Screen.ShopkeeperApplications.route) {
            ShopkeeperApplicationsScreen(
                onBackClick = {
                    navController.popBackStack()
                },
                onNavigateTab = { tab ->
                    when (tab) {
                        ShopkeeperTab.HOME -> navController.navigateTab(Screen.ShopkeeperHome.route, Screen.ShopkeeperHome.route)
                        ShopkeeperTab.JOBS -> navController.navigateTab(Screen.ShopkeeperHome.route, Screen.ShopkeeperMyJobs.route)
                        ShopkeeperTab.APPLICATIONS -> navController.navigateTab(Screen.ShopkeeperHome.route, Screen.ShopkeeperApplications.route)
                        ShopkeeperTab.PROFILE -> navController.navigateTab(Screen.ShopkeeperHome.route, Screen.ShopkeeperProfile.route)
                    }
                }
            )
        }

        composable(Screen.ShopkeeperProfile.route) {
            LaunchedEffect(Unit) { shopkeeperViewModel.refreshProfile() }
            ShopkeeperProfileScreen(
                state = shopkeeperState,
                onSaveProfile = { name, shop ->
                    scope.launch {
                        try { shopkeeperViewModel.saveProfile(name, shop); Toast.makeText(context, "Profile saved", Toast.LENGTH_SHORT).show() }
                        catch (error: Exception) { Toast.makeText(context, error.localizedMessage ?: "Unable to save profile", Toast.LENGTH_LONG).show() }
                    }
                },
                onBackClick = {
                    navController.popBackStack()
                },
                onLogoutClick = {
                    scope.launch {
                        runCatching { FirebaseGoogleAuth.logout() }
                        navController.navigate(Screen.RoleSelection.route) {
                            popUpTo(0)
                        }
                    }
                },
                onNavigateTab = { tab ->
                    when (tab) {
                        ShopkeeperTab.HOME -> navController.navigateTab(Screen.ShopkeeperHome.route, Screen.ShopkeeperHome.route)
                        ShopkeeperTab.JOBS -> navController.navigateTab(Screen.ShopkeeperHome.route, Screen.ShopkeeperMyJobs.route)
                        ShopkeeperTab.APPLICATIONS -> navController.navigateTab(Screen.ShopkeeperHome.route, Screen.ShopkeeperApplications.route)
                        ShopkeeperTab.PROFILE -> navController.navigateTab(Screen.ShopkeeperHome.route, Screen.ShopkeeperProfile.route)
                    }
                }
            )
        }

        // Worker Flow Routes
        composable(Screen.WorkerHome.route) {
            LaunchedEffect(Unit) { workerViewModel.refreshBackendJobs() }
            WorkerHomeScreen(
                state = workerState,
                onJobSelect = { job ->
                    workerViewModel.selectJob(job)
                    navController.navigate(Screen.WorkerJobDetails.route)
                },
                onRefresh = { scope.launch { workerViewModel.refreshBackendJobs() } },
                onNavigateTab = { tab ->
                    when (tab) {
                        WorkerTab.HOME -> navController.navigateTab(Screen.WorkerHome.route, Screen.WorkerHome.route)
                        WorkerTab.MY_JOBS -> navController.navigateTab(Screen.WorkerHome.route, Screen.WorkerMyJobs.route)
                        WorkerTab.EARNINGS -> navController.navigateTab(Screen.WorkerHome.route, Screen.WorkerEarnings.route)
                        WorkerTab.PROFILE -> navController.navigateTab(Screen.WorkerHome.route, Screen.WorkerProfile.route)
                    }
                }
            )
        }

        composable(Screen.WorkerJobDetails.route) {
            WorkerJobDetailsScreen(
                state = workerState,
                onBackClick = {
                    navController.popBackStack()
                },
                onDurationSelect = workerViewModel::selectDurationPay,
                onStartJobClick = { scope.launch { workerViewModel.startAssignedJob(workerState.selectedJob?.id.orEmpty()) } },
                onAcceptJobClick = {
                    scope.launch {
                        try {
                            workerViewModel.acceptCurrentJob()
                            navController.navigate(Screen.WorkerAcceptingJob.route)
                        } catch (error: Exception) {
                            Toast.makeText(context, error.localizedMessage ?: "Unable to apply. Retry.", Toast.LENGTH_LONG).show()
                        }
                    }
                }
            )
        }

        composable(Screen.WorkerAcceptingJob.route) {
            WorkerAcceptingJobScreen(
                state = workerState,
                onViewJobInfoClick = {
                    navController.navigate(Screen.WorkerMyJobs.route) {
                        popUpTo(Screen.WorkerHome.route)
                    }
                }
            )
        }

        composable(Screen.WorkerMyJobs.route) {
            LaunchedEffect(Unit) {
                workerViewModel.refreshBackendJobs()
                workerViewModel.refreshApplications()
            }
            WorkerMyJobsScreen(
                state = workerState,
                onBackClick = {
                    navController.popBackStack()
                },
                onJobClick = { job ->
                    workerViewModel.selectJob(job)
                    navController.navigate(Screen.WorkerJobDetails.route)
                },
                onCancelApplication = { application -> scope.launch { workerViewModel.cancelApplication(application) } },
                onLoadMoreApplications = { scope.launch { workerViewModel.loadMoreApplications() } },
                onRateShopkeeperClick = workerViewModel::rateShopkeeper,
                onNavigateTab = { tab ->
                    when (tab) {
                        WorkerTab.HOME -> navController.navigateTab(Screen.WorkerHome.route, Screen.WorkerHome.route)
                        WorkerTab.MY_JOBS -> navController.navigateTab(Screen.WorkerHome.route, Screen.WorkerMyJobs.route)
                        WorkerTab.EARNINGS -> navController.navigateTab(Screen.WorkerHome.route, Screen.WorkerEarnings.route)
                        WorkerTab.PROFILE -> navController.navigateTab(Screen.WorkerHome.route, Screen.WorkerProfile.route)
                    }
                }
            )
        }

        composable(Screen.WorkerEarnings.route) {
            WorkerEarningsScreen(
                state = workerState,
                onBackClick = {
                    navController.popBackStack()
                },
                onNavigateTab = { tab ->
                    when (tab) {
                        WorkerTab.HOME -> navController.navigateTab(Screen.WorkerHome.route, Screen.WorkerHome.route)
                        WorkerTab.MY_JOBS -> navController.navigateTab(Screen.WorkerHome.route, Screen.WorkerMyJobs.route)
                        WorkerTab.EARNINGS -> navController.navigateTab(Screen.WorkerHome.route, Screen.WorkerEarnings.route)
                        WorkerTab.PROFILE -> navController.navigateTab(Screen.WorkerHome.route, Screen.WorkerProfile.route)
                    }
                }
            )
        }

        composable(Screen.WorkerProfile.route) {
            WorkerProfileScreen(
                state = workerState,
                onBackClick = {
                    navController.popBackStack()
                },
                onLogoutClick = {
                    scope.launch {
                        runCatching { FirebaseGoogleAuth.logout() }
                        navController.navigate(Screen.RoleSelection.route) {
                            popUpTo(0)
                        }
                    }
                },
                onDigiLockerClick = {
                    navController.navigate(Screen.DigiLockerVerification.route)
                },
                onNavigateTab = { tab ->
                    when (tab) {
                        WorkerTab.HOME -> navController.navigateTab(Screen.WorkerHome.route, Screen.WorkerHome.route)
                        WorkerTab.MY_JOBS -> navController.navigateTab(Screen.WorkerHome.route, Screen.WorkerMyJobs.route)
                        WorkerTab.EARNINGS -> navController.navigateTab(Screen.WorkerHome.route, Screen.WorkerEarnings.route)
                        WorkerTab.PROFILE -> navController.navigateTab(Screen.WorkerHome.route, Screen.WorkerProfile.route)
                    }
                }
            )
        }

        composable(Screen.DigiLockerVerification.route) {
            DigiLockerVerificationScreen(
                isAlreadyVerified = workerState.isDigiLockerVerified,
                aadhaarMasked = workerState.aadhaarMasked,
                onBackClick = {
                    navController.popBackStack()
                },
                onVerificationSuccess = { aadhaarNum ->
                    workerViewModel.verifyDigiLockerAadhaar(aadhaarNum)
                }
            )
        }

        // Existing routes
        composable(Screen.Home.route) {
            HomeScreen()
        }
    }
}

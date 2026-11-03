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
import com.erno.app.ui.screens.payment.RazorpayPaymentScreen
import com.erno.app.data.repository.FirebaseGoogleAuth
import com.erno.app.data.repository.WhatsAppAuthApi
import com.erno.app.data.repository.ErrnoMobileApi
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
    var otpSending by remember { mutableStateOf(false) }
    fun openPendingNotification() {
        val activity = context as? com.erno.app.MainActivity ?: return
        if (activity.intent?.hasExtra("notification_route") == true) {
            navController.navigate(Screen.Notifications.route) { launchSingleTop = true }
            activity.intent.removeExtra("notification_route")
            activity.intent.removeExtra("notification_job_id")
            activity.intent.removeExtra("notification_payment_id")
            activity.intent.removeExtra("notification_kyc_id")
        }
    }
    LaunchedEffect(Unit) {
        runCatching { FirebaseGoogleAuth.restore() }.getOrNull()?.let { identity ->
            val route = when (identity.role) {
                "worker" -> Screen.WorkerHome.route
                "shopkeeper", "shop_owner" -> Screen.ShopkeeperHome.route
                else -> Screen.RoleSelection.route
            }
            navController.navigate(route) { popUpTo(Screen.RoleSelection.route) { inclusive = true } }
            openPendingNotification()
            (context as? com.erno.app.MainActivity)?.startPresenceTracking()
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
                openPendingNotification()
                (context as? com.erno.app.MainActivity)?.startPresenceTracking()
            } catch (error: Exception) {
                if (error !is CancellationException && error !is GetCredentialCancellationException) {
                    Toast.makeText(context, error.localizedMessage ?: "Google sign-in failed. Please retry.", Toast.LENGTH_LONG).show()
                }
            } finally {
                googleLoading = false
            }
        }
    }
    fun sendPhoneOtp(phone: String, selectedRole: String, fullName: String? = null) {
        if (otpSending) return
        otpSending = true
        scope.launch {
            try {
                val challenge = WhatsAppAuthApi.send(phone, selectedRole)
                val encodedPhone = android.net.Uri.encode(phone)
                val encodedName = android.net.Uri.encode(fullName.orEmpty())
                navController.navigate("verify_otp/$encodedPhone?role=$selectedRole&requestId=${challenge.requestId}&expires=${challenge.expiresInSeconds}&resend=${challenge.resendAfterSeconds}&fullName=$encodedName")
            } catch (error: Exception) {
                Toast.makeText(context, error.localizedMessage ?: "WhatsApp OTP is unavailable.", Toast.LENGTH_LONG).show()
            } finally { otpSending = false }
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
                    sendPhoneOtp(phoneNumber, "shopkeeper")
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
                    sendPhoneOtp(phoneNumber, "worker")
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
                onRegisterClick = { fullName, phoneNumber, role ->
                    val roleParam = if (role == Role.WORKER) "worker" else "shopkeeper"
                    sendPhoneOtp(phoneNumber, roleParam, fullName)
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
            route = "verify_otp/{phoneNumber}?role={role}&requestId={requestId}&expires={expires}&resend={resend}&fullName={fullName}",
            arguments = listOf(
                navArgument("phoneNumber") { type = NavType.StringType },
                navArgument("role") {
                    type = NavType.StringType
                    defaultValue = "shopkeeper"
                },
                navArgument("requestId") { type = NavType.StringType },
                navArgument("expires") { type = NavType.IntType; defaultValue = 300 },
                navArgument("resend") { type = NavType.IntType; defaultValue = 30 },
                navArgument("fullName") { type = NavType.StringType; defaultValue = "" }
            )
        ) { backStackEntry ->
            val phoneNumber = backStackEntry.arguments?.getString("phoneNumber") ?: ""
            val role = backStackEntry.arguments?.getString("role") ?: "shopkeeper"
            val requestId = backStackEntry.arguments?.getString("requestId") ?: ""

            VerifyOTPScreen(
                phoneNumber = phoneNumber,
                initialRequestId = requestId,
                expiresInSeconds = backStackEntry.arguments?.getInt("expires") ?: 300,
                resendAfterSeconds = backStackEntry.arguments?.getInt("resend") ?: 30,
                onBackClick = {
                    navController.popBackStack()
                },
                onVerifyClick = { otp, activeRequestId ->
                    val identity = WhatsAppAuthApi.verify(phoneNumber, role, activeRequestId, otp, backStackEntry.arguments?.getString("fullName"))
                    runCatching { com.erno.app.notifications.ErrnoNotificationDeviceSync.registerCurrent() }
                    runCatching { ErrnoMobileApi.presenceHeartbeat(true) }
                    (context as? com.erno.app.MainActivity)?.startPresenceTracking()
                    val home = if (identity.role == "worker") Screen.WorkerHome.route else Screen.ShopkeeperHome.route
                    navController.navigate(home) { popUpTo(Screen.RoleSelection.route) { inclusive = true } }
                    openPendingNotification()
                },
                onEditClick = {
                    navController.popBackStack()
                },
                onResendClick = { activeRequestId ->
                    WhatsAppAuthApi.resend(phoneNumber, role, activeRequestId)
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
                onNotifications = { navController.navigate(Screen.Notifications.route) },
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

        composable(Screen.Notifications.route) {
            com.erno.app.ui.screens.notifications.NotificationInboxScreen(onBack = { navController.popBackStack() })
        }

        composable(Screen.PostJob.route) {
            LaunchedEffect(Unit) { shopkeeperViewModel.refreshPricing() }
            PostJobScreen(
                state = shopkeeperState,
                onBackClick = {
                    navController.popBackStack()
                },
                onCategoryChange = shopkeeperViewModel::updateCategory,
                onLocationChange = shopkeeperViewModel::updateLocation,
                onScheduledDateChange = shopkeeperViewModel::updateScheduledDate,
                onScheduledTimeChange = shopkeeperViewModel::updateScheduledTime,
                onWorkingRequirementTypeChange = shopkeeperViewModel::updateWorkingRequirementType,
                onBookingTypeChange = shopkeeperViewModel::updateBookingType,
                onPickupLocationChange = shopkeeperViewModel::updatePickupLocation,
                onDropLocationChange = shopkeeperViewModel::updateDropLocation,
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
            LaunchedEffect(
                shopkeeperState.draftPayStructure.firstOrNull()?.hours,
                shopkeeperState.draftScheduledDate,
                shopkeeperState.draftScheduledTime,
                shopkeeperState.draftBookingType,
                shopkeeperState.draftWorkingRequirementType,
                shopkeeperState.draftPickupLocation,
                shopkeeperState.draftLocation
            ) {
                runCatching { shopkeeperViewModel.refreshQuote() }.onFailure { error ->
                    // Leave the quote absent so confirmation stays disabled and show the API error below.
                    shopkeeperViewModel.setError(error.localizedMessage ?: "Unable to quote this job.")
                }
            }
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
                            workerViewModel.refreshBackendJobs()
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
                onPayJob = { bookingId -> navController.navigate(Screen.PaymentCheckout.createRoute(bookingId)) },
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

        composable(Screen.PaymentCheckout.route, arguments = listOf(navArgument("bookingId") { type = NavType.StringType })) { entry ->
            RazorpayPaymentScreen(bookingId = entry.arguments?.getString("bookingId").orEmpty(), onBack = { navController.popBackStack() })
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
                        (context as? com.erno.app.MainActivity)?.stopPresenceTracking()
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
            LaunchedEffect(Unit) { workerViewModel.refreshBackendJobs(); workerViewModel.refreshAvailability() }
            WorkerHomeScreen(
                state = workerState,
                onJobSelect = { job ->
                    workerViewModel.selectJob(job)
                    navController.navigate(Screen.WorkerJobDetails.route)
                },
                onToggleOnlineStatus = { available -> scope.launch {
                    runCatching { workerViewModel.setAvailableForWork(available) }
                        .onFailure { Toast.makeText(context, it.localizedMessage ?: "Availability update failed", Toast.LENGTH_LONG).show() }
                } },
                onRefresh = { scope.launch { workerViewModel.refreshBackendJobs() } },
                onNavigateTab = { tab ->
                    when (tab) {
                        WorkerTab.HOME -> navController.navigateTab(Screen.WorkerHome.route, Screen.WorkerHome.route)
                        WorkerTab.MY_JOBS -> navController.navigateTab(Screen.WorkerHome.route, Screen.WorkerMyJobs.route)
                        WorkerTab.EARNINGS -> navController.navigateTab(Screen.WorkerHome.route, Screen.WorkerEarnings.route)
                        WorkerTab.PROFILE -> navController.navigateTab(Screen.WorkerHome.route, Screen.WorkerProfile.route)
                    }
                },
                onNotifications = { navController.navigate(Screen.Notifications.route) }
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
            LaunchedEffect(Unit) { workerViewModel.refreshKycStatus() }
            WorkerProfileScreen(
                state = workerState,
                onBackClick = {
                    navController.popBackStack()
                },
                onLogoutClick = {
                    scope.launch {
                        runCatching { FirebaseGoogleAuth.logout() }
                        (context as? com.erno.app.MainActivity)?.stopPresenceTracking()
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
                onBackClick = {
                    navController.popBackStack()
                },
                onStatusRefreshed = { scope.launch { workerViewModel.refreshKycStatus() } }
            )
        }

        // Existing routes
        composable(Screen.Home.route) {
            HomeScreen()
        }
    }
}

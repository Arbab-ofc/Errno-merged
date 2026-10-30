package com.erno.app.ui.screens.shopkeeper

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.erno.app.ui.components.ShopkeeperBottomNavigation
import com.erno.app.ui.components.ShopkeeperTab
import com.erno.app.ui.components.WorkerLocationMapView
import com.erno.app.ui.theme.ErnoGreen
import com.erno.app.ui.theme.ErnoTextSecondary

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ShopkeeperProfileScreen(
    state: ShopkeeperState,
    onSaveProfile: (String, String) -> Unit,
    onBackClick: () -> Unit,
    onLogoutClick: () -> Unit,
    onNavigateTab: (ShopkeeperTab) -> Unit
) {
    val context = LocalContext.current
    var showEditDetailsDialog by remember { mutableStateOf(false) }
    var showStoreLocationDialog by remember { mutableStateOf(false) }
    var showHelpSupportDialog by remember { mutableStateOf(false) }
    var showTermsPrivacyDialog by remember { mutableStateOf(false) }
    var showLogoutConfirmDialog by remember { mutableStateOf(false) }

    var ownerNameInput by remember(state.ownerName) { mutableStateOf(state.ownerName) }
    var storeNameInput by remember(state.shopName) { mutableStateOf(state.shopName) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "Profile & Business Settings",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.Black
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back",
                            tint = Color.Black
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color.White)
            )
        },
        bottomBar = {
            ShopkeeperBottomNavigation(
                selectedTab = ShopkeeperTab.PROFILE,
                onTabSelected = onNavigateTab
            )
        },
        containerColor = Color(0xFFF9FAFB)
    ) { paddingValues ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(horizontal = 20.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Profile Header Card
            item {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(20.dp),
                    color = Color.White,
                    shadowElevation = 1.dp
                ) {
                    Column(
                        modifier = Modifier.padding(20.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Box(
                            modifier = Modifier
                                .size(72.dp)
                                .background(Color(0xFFF1F8E9), CircleShape),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.Storefront,
                                contentDescription = null,
                                tint = ErnoGreen,
                                modifier = Modifier.size(36.dp)
                            )
                        }

                        Spacer(modifier = Modifier.height(12.dp))

                        Text(
                            text = ownerNameInput,
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.Black
                        )

                        Text(
                            text = storeNameInput,
                            fontSize = 14.sp,
                            color = ErnoTextSecondary
                        )

                        Spacer(modifier = Modifier.height(6.dp))

                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.Default.LocationOn,
                                contentDescription = null,
                                tint = Color.Gray,
                                modifier = Modifier.size(14.dp)
                            )
                            Spacer(modifier = Modifier.width(4.dp))
                            Text(
                                text = state.shopAddress.ifBlank { "Store address not set" },
                                fontSize = 12.sp,
                                color = Color.Gray
                            )
                        }

                        Spacer(modifier = Modifier.height(12.dp))

                        Surface(
                            shape = RoundedCornerShape(12.dp),
                            color = Color(0xFFE8F5E9)
                        ) {
                            Row(
                                modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Verified,
                                    contentDescription = null,
                                    tint = Color(0xFF2E7D32),
                                    modifier = Modifier.size(14.dp)
                                )
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(
                                text = "Firebase account linked",
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF2E7D32)
                                )
                            }
                        }
                    }
                }
            }

            // Stats Row (All 0 Initially)
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    ProfileStatCard("Total Posted", "${state.recentJobs.size}", Modifier.weight(1f))
                    ProfileStatCard("Active Jobs", "${state.activeJobsCount}", Modifier.weight(1f))
                    ProfileStatCard("Rating", "0", Modifier.weight(1f))
                }
            }

            // Working Settings Options List
            item {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    color = Color.White,
                    shadowElevation = 1.dp
                ) {
                    Column(modifier = Modifier.padding(vertical = 8.dp)) {
                        ProfileOptionItem(
                            icon = Icons.Default.Edit,
                            title = "Edit Business Details",
                            onClick = { showEditDetailsDialog = true }
                        )
                        HorizontalDivider(color = Color(0xFFF5F5F5))
                        ProfileOptionItem(
                            icon = Icons.Default.Storefront,
                            title = "Store Location & Timings",
                            onClick = { showStoreLocationDialog = true }
                        )
                        HorizontalDivider(color = Color(0xFFF5F5F5))
                        ProfileOptionItem(
                            icon = Icons.Default.HelpOutline,
                            title = "Help & Support Center",
                            onClick = { showHelpSupportDialog = true }
                        )
                        HorizontalDivider(color = Color(0xFFF5F5F5))
                        ProfileOptionItem(
                            icon = Icons.Default.Security,
                            title = "Terms of Service & Privacy",
                            onClick = { showTermsPrivacyDialog = true }
                        )
                    }
                }
            }

            // Logout Button
            item {
                Button(
                    onClick = { showLogoutConfirmDialog = true },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(50.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFFFEBEE)),
                    shape = RoundedCornerShape(12.dp),
                    elevation = ButtonDefaults.buttonElevation(defaultElevation = 0.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Logout,
                        contentDescription = null,
                        tint = Color(0xFFD32F2F),
                        modifier = Modifier.size(18.dp)
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "Logout Account",
                        fontSize = 15.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFFD32F2F)
                    )
                }
            }
        }
    }

    // 1. EDIT BUSINESS DETAILS DIALOG
    if (showEditDetailsDialog) {
        AlertDialog(
            onDismissRequest = { showEditDetailsDialog = false },
            containerColor = Color.White,
            titleContentColor = Color.Black,
            textContentColor = Color.Black,
            title = { Text("Edit Business Details", fontWeight = FontWeight.Bold, color = Color.Black) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(
                        value = ownerNameInput,
                        onValueChange = { ownerNameInput = it },
                        label = { Text("Owner Name", color = Color.Gray) },
                        textStyle = LocalTextStyle.current.copy(color = Color.Black),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedTextColor = Color.Black,
                            unfocusedTextColor = Color.Black,
                            focusedBorderColor = ErnoGreen,
                            unfocusedBorderColor = Color(0xFFD0D0D0)
                        ),
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(10.dp)
                    )
                    OutlinedTextField(
                        value = storeNameInput,
                        onValueChange = { storeNameInput = it },
                        label = { Text("Store / Business Name", color = Color.Gray) },
                        textStyle = LocalTextStyle.current.copy(color = Color.Black),
                        colors = OutlinedTextFieldDefaults.colors(
                            focusedTextColor = Color.Black,
                            unfocusedTextColor = Color.Black,
                            focusedBorderColor = ErnoGreen,
                            unfocusedBorderColor = Color(0xFFD0D0D0)
                        ),
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(10.dp)
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        onSaveProfile(ownerNameInput, storeNameInput)
                        showEditDetailsDialog = false
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = ErnoGreen),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text("Save Details", color = Color.White)
                }
            },
            dismissButton = {
                TextButton(onClick = { showEditDetailsDialog = false }) { Text("Cancel", color = Color.Gray) }
            }
        )
    }

    // 2. STORE LOCATION & TIMINGS DIALOG
    if (showStoreLocationDialog) {
        AlertDialog(
            onDismissRequest = { showStoreLocationDialog = false },
            containerColor = Color.White,
            titleContentColor = Color.Black,
            textContentColor = Color.Black,
            title = { Text("Store Location & Working Hours", fontWeight = FontWeight.Bold, color = Color.Black) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text("📍 Address: ${state.shopAddress.ifBlank { "Not set" }}", fontSize = 13.sp, color = Color.Black)
                    Text("🕒 Working Hours: 08:00 AM - 09:00 PM (Mon - Sat)", fontSize = 13.sp, color = Color.Black)
                    WorkerLocationMapView(
                        locationName = "Store Location Map Pin",
                        distanceText = "Block B Okhla",
                        isDarkTheme = false
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = { showStoreLocationDialog = false },
                    colors = ButtonDefaults.buttonColors(containerColor = ErnoGreen),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text("Close", color = Color.White)
                }
            }
        )
    }

    // 4. HELP & SUPPORT CENTER DIALOG
    if (showHelpSupportDialog) {
        AlertDialog(
            onDismissRequest = { showHelpSupportDialog = false },
            containerColor = Color.White,
            titleContentColor = Color.Black,
            textContentColor = Color.Black,
            title = { Text("ERRNO Support Center", fontWeight = FontWeight.Bold, color = Color.Black) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text("Need help with job posting, worker settlements, or app issues?", fontSize = 13.sp, color = Color.DarkGray)
                    
                    Button(
                        onClick = {
                            val intent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:+919971439107"))
                            context.startActivity(intent)
                        },
                        modifier = Modifier.fillMaxWidth(),
                        colors = ButtonDefaults.buttonColors(containerColor = ErnoGreen)
                    ) {
                        Icon(Icons.Default.Phone, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Call Support (+91 9971439107)")
                    }

                    OutlinedButton(
                        onClick = {
                            val intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://wa.me/919971439107"))
                            context.startActivity(intent)
                        },
                        modifier = Modifier.fillMaxWidth(),
                        border = BorderStroke(1.dp, ErnoGreen)
                    ) {
                        Text("WhatsApp Chat Support", color = ErnoGreen, fontWeight = FontWeight.Bold)
                    }

                    OutlinedButton(
                        onClick = {
                            val emailIntent = Intent(Intent.ACTION_SENDTO).apply {
                                data = Uri.parse("mailto:support.errno@gmail.com")
                                putExtra(Intent.EXTRA_SUBJECT, "ERRNO Support Request")
                            }
                            try {
                                context.startActivity(emailIntent)
                            } catch (_: Exception) {}
                        },
                        modifier = Modifier.fillMaxWidth(),
                        border = BorderStroke(1.dp, ErnoGreen)
                    ) {
                        Icon(Icons.Default.Email, contentDescription = null, modifier = Modifier.size(16.dp), tint = ErnoGreen)
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("Email Support (support.errno@gmail.com)", color = ErnoGreen, fontWeight = FontWeight.Bold)
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { showHelpSupportDialog = false }) { Text("Close", color = Color.Gray) }
            }
        )
    }

    // 5. TERMS OF SERVICE & PRIVACY POLICY DIALOG
    if (showTermsPrivacyDialog) {
        AlertDialog(
            onDismissRequest = { showTermsPrivacyDialog = false },
            containerColor = Color.White,
            titleContentColor = Color.Black,
            textContentColor = Color.Black,
            title = { Text("Terms of Service & Privacy Policy", fontWeight = FontWeight.Bold, color = Color.Black) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("• Privacy Protection: ERRNO respects user privacy and secures location and phone details.", fontSize = 12.sp, color = Color.DarkGray)
                    Text("• Worker Settlements: Job payment settlements are paid directly to verified workers upon job completion.", fontSize = 12.sp, color = Color.DarkGray)
                    Text("• Pre-Booking Policy: Pre-booked shifts can be scheduled up to 6 days in advance.", fontSize = 12.sp, color = Color.DarkGray)
                }
            },
            confirmButton = {
                Button(
                    onClick = { showTermsPrivacyDialog = false },
                    colors = ButtonDefaults.buttonColors(containerColor = ErnoGreen)
                ) {
                    Text("I Agree")
                }
            }
        )
    }

    // 6. LOGOUT CONFIRMATION DIALOG
    if (showLogoutConfirmDialog) {
        AlertDialog(
            onDismissRequest = { showLogoutConfirmDialog = false },
            containerColor = Color.White,
            titleContentColor = Color.Black,
            textContentColor = Color.Black,
            title = { Text("Logout Account", fontWeight = FontWeight.Bold, color = Color.Black) },
            text = { Text("Are you sure you want to log out of your ERRNO account?", fontSize = 14.sp, color = Color.Black) },
            confirmButton = {
                Button(
                    onClick = {
                        showLogoutConfirmDialog = false
                        onLogoutClick()
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFD32F2F))
                ) {
                    Text("Yes, Logout", color = Color.White, fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                TextButton(onClick = { showLogoutConfirmDialog = false }) { Text("Cancel", color = Color.Gray) }
            }
        )
    }
}

@Composable
fun ProfileStatCard(label: String, value: String, modifier: Modifier = Modifier) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(14.dp),
        color = Color.White,
        shadowElevation = 1.dp
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = value,
                fontSize = 16.sp,
                fontWeight = FontWeight.Bold,
                color = Color.Black
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = label,
                fontSize = 11.sp,
                color = ErnoTextSecondary
            )
        }
    }
}

@Composable
fun ProfileOptionItem(
    icon: ImageVector,
    title: String,
    onClick: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() }
            .padding(horizontal = 16.dp, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(
            imageVector = icon,
            contentDescription = null,
            tint = ErnoGreen,
            modifier = Modifier.size(20.dp)
        )
        Spacer(modifier = Modifier.width(14.dp))
        Text(
            text = title,
            fontSize = 14.sp,
            fontWeight = FontWeight.Medium,
            color = Color.Black,
            modifier = Modifier.weight(1f)
        )
        Icon(
            imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
            contentDescription = null,
            tint = Color.Gray,
            modifier = Modifier.size(18.dp)
        )
    }
}

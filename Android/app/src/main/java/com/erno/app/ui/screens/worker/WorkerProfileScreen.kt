package com.erno.app.ui.screens.worker

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
import com.erno.app.ui.components.WorkerBottomNavigation
import com.erno.app.ui.components.WorkerTab
import com.erno.app.ui.theme.ErnoGreen
import com.erno.app.ui.theme.ErnoTextSecondary

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WorkerProfileScreen(
    state: WorkerState,
    onBackClick: () -> Unit,
    onLogoutClick: () -> Unit,
    onNavigateTab: (WorkerTab) -> Unit,
    onDigiLockerClick: () -> Unit = {}
) {
    val context = LocalContext.current
    var showEditDetailsDialog by remember { mutableStateOf(false) }
    var showSkillsDialog by remember { mutableStateOf(false) }
    var showBankPayoutDialog by remember { mutableStateOf(false) }
    var showHelpSupportDialog by remember { mutableStateOf(false) }
    var showTermsPrivacyDialog by remember { mutableStateOf(false) }
    var showLogoutConfirmDialog by remember { mutableStateOf(false) }

    var workerNameInput by remember { mutableStateOf(state.workerName) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "Worker Profile Settings",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "Back",
                            tint = Color.White
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Color(0xFF0B121F))
            )
        },
        bottomBar = {
            WorkerBottomNavigation(
                selectedTab = WorkerTab.PROFILE,
                onTabSelected = onNavigateTab,
                containerColor = Color(0xFF0E1726),
                contentColor = ErnoGreen
            )
        },
        containerColor = Color(0xFF0B121F)
    ) { paddingValues ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .padding(horizontal = 20.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Profile Card
            item {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(20.dp),
                    color = Color.White
                ) {
                    Column(
                        modifier = Modifier.padding(20.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Box(
                            modifier = Modifier
                                .size(72.dp)
                                .background(Color(0xFFEAF5D8), CircleShape),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.Engineering,
                                contentDescription = null,
                                tint = ErnoGreen,
                                modifier = Modifier.size(36.dp)
                            )
                        }

                        Spacer(modifier = Modifier.height(12.dp))

                        Text(
                            text = workerNameInput,
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Bold,
                            color = Color.Black
                        )

                        Text(
                            text = "Experienced Delivery Partner & Helper",
                            fontSize = 13.sp,
                            color = ErnoTextSecondary
                        )

                        Spacer(modifier = Modifier.height(8.dp))

                        Surface(
                            shape = RoundedCornerShape(12.dp),
                            color = if (state.isDigiLockerVerified) Color(0xFFE8F5E9) else Color(0xFFFFF3E0)
                        ) {
                            Row(
                                modifier = Modifier.padding(horizontal = 12.dp, vertical = 4.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Icon(
                                    imageVector = if (state.isDigiLockerVerified) Icons.Default.Verified else Icons.Default.Shield,
                                    contentDescription = null,
                                    tint = if (state.isDigiLockerVerified) Color(0xFF2E7D32) else Color(0xFFE65100),
                                    modifier = Modifier.size(14.dp)
                                )
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(
                                    text = if (state.isDigiLockerVerified) "DigiLocker Verified SEIF Worker" else "DigiLocker Verification Pending",
                                    fontSize = 12.sp,
                                    fontWeight = FontWeight.Bold,
                                    color = if (state.isDigiLockerVerified) Color(0xFF2E7D32) else Color(0xFFE65100)
                                )
                            }
                        }
                    }
                }
            }

            // Stats Row (00 Jobs, ₹0 Earned, 0.0 Rating Initially)
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    WorkerProfileStatCard("Jobs Completed", String.format("%02d", state.jobsCompletedCount), Modifier.weight(1f))
                    WorkerProfileStatCard("Total Earned", "₹${state.totalEarnings}", Modifier.weight(1f))
                    WorkerProfileStatCard("Rating", "${state.workerRating} ★", Modifier.weight(1f))
                }
            }

            // Settings Options List
            item {
                Surface(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(16.dp),
                    color = Color.White
                ) {
                    Column(modifier = Modifier.padding(vertical = 8.dp)) {
                        WorkerProfileOptionItem(
                            icon = Icons.Default.Shield,
                            title = "DigiLocker Aadhaar Verification",
                            onClick = onDigiLockerClick
                        )
                        HorizontalDivider(color = Color(0xFFF5F5F5))
                        WorkerProfileOptionItem(
                            icon = Icons.Default.Person,
                            title = "Edit Personal Details",
                            onClick = { showEditDetailsDialog = true }
                        )
                        HorizontalDivider(color = Color(0xFFF5F5F5))
                        WorkerProfileOptionItem(
                            icon = Icons.Default.Engineering,
                            title = "My Skills & Preferred Work",
                            onClick = { showSkillsDialog = true }
                        )
                        HorizontalDivider(color = Color(0xFFF5F5F5))
                        WorkerProfileOptionItem(
                            icon = Icons.Default.AccountBalance,
                            title = "Bank Account & Payout Details",
                            onClick = { showBankPayoutDialog = true }
                        )
                        HorizontalDivider(color = Color(0xFFF5F5F5))
                        WorkerProfileOptionItem(
                            icon = Icons.Default.HelpOutline,
                            title = "Help & Support",
                            onClick = { showHelpSupportDialog = true }
                        )
                        HorizontalDivider(color = Color(0xFFF5F5F5))
                        WorkerProfileOptionItem(
                            icon = Icons.Default.Security,
                            title = "Terms & Privacy Policy",
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

    // 1. EDIT PERSONAL DETAILS DIALOG
    if (showEditDetailsDialog) {
        AlertDialog(
            onDismissRequest = { showEditDetailsDialog = false },
            containerColor = Color.White,
            titleContentColor = Color.Black,
            textContentColor = Color.Black,
            title = { Text("Edit Personal Details", fontWeight = FontWeight.Bold, color = Color.Black) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(
                        value = workerNameInput,
                        onValueChange = { workerNameInput = it },
                        label = { Text("Worker Full Name", color = Color.Gray) },
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
                    onClick = { showEditDetailsDialog = false },
                    colors = ButtonDefaults.buttonColors(containerColor = ErnoGreen),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text("Save", color = Color.White)
                }
            },
            dismissButton = {
                TextButton(onClick = { showEditDetailsDialog = false }) { Text("Cancel", color = Color.Gray) }
            }
        )
    }

    // 2. SKILLS & PREFERRED WORK DIALOG
    if (showSkillsDialog) {
        AlertDialog(
            onDismissRequest = { showSkillsDialog = false },
            containerColor = Color.White,
            titleContentColor = Color.Black,
            textContentColor = Color.Black,
            title = { Text("My Work Skills", fontWeight = FontWeight.Bold, color = Color.Black) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("✓ Express Delivery Partner", fontSize = 13.sp, color = Color.Black)
                    Text("✓ Shop Assistant & Packing", fontSize = 13.sp, color = Color.Black)
                    Text("✓ Store Counter Staff", fontSize = 13.sp, color = Color.Black)
                }
            },
            confirmButton = {
                Button(
                    onClick = { showSkillsDialog = false },
                    colors = ButtonDefaults.buttonColors(containerColor = ErnoGreen)
                ) {
                    Text("OK", color = Color.White)
                }
            }
        )
    }

    // 3. BANK ACCOUNT & PAYOUT DETAILS
    if (showBankPayoutDialog) {
        AlertDialog(
            onDismissRequest = { showBankPayoutDialog = false },
            containerColor = Color.White,
            titleContentColor = Color.Black,
            textContentColor = Color.Black,
            title = { Text("Withdrawal UPI & Bank Details", fontWeight = FontWeight.Bold, color = Color.Black) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Surface(shape = RoundedCornerShape(10.dp), color = Color(0xFFEAF5D8), modifier = Modifier.fillMaxWidth()) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Text("Linked Payout UPI / Bank:", fontSize = 12.sp, color = Color.Gray)
                            Text("amanworker@upi", fontSize = 16.sp, fontWeight = FontWeight.Bold, color = ErnoGreen)
                        }
                    }
                    Text("✓ Instant earnings transfer available to UPI or Bank account.", fontSize = 12.sp, color = Color.DarkGray)
                }
            },
            confirmButton = {
                Button(
                    onClick = { showBankPayoutDialog = false },
                    colors = ButtonDefaults.buttonColors(containerColor = ErnoGreen)
                ) {
                    Text("Close", color = Color.White)
                }
            }
        )
    }

    // 4. HELP & SUPPORT DIALOG
    if (showHelpSupportDialog) {
        AlertDialog(
            onDismissRequest = { showHelpSupportDialog = false },
            containerColor = Color.White,
            titleContentColor = Color.Black,
            textContentColor = Color.Black,
            title = { Text("ERRNO Worker Support", fontWeight = FontWeight.Bold, color = Color.Black) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text("Need help with job shifts, earnings withdrawal, or shop location directions?", fontSize = 13.sp, color = Color.DarkGray)
                    
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
                        Text("WhatsApp Support", color = ErnoGreen, fontWeight = FontWeight.Bold)
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

    // 5. TERMS & PRIVACY POLICY DIALOG
    if (showTermsPrivacyDialog) {
        AlertDialog(
            onDismissRequest = { showTermsPrivacyDialog = false },
            containerColor = Color.White,
            titleContentColor = Color.Black,
            textContentColor = Color.Black,
            title = { Text("Terms & Privacy Policy", fontWeight = FontWeight.Bold, color = Color.Black) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("• Fair Wages: Payouts are transferred immediately after shift completion.", fontSize = 12.sp, color = Color.DarkGray)
                    Text("• Privacy: Location is used strictly for showing job routes near you.", fontSize = 12.sp, color = Color.DarkGray)
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
            text = { Text("Are you sure you want to log out of your ERRNO worker account?", fontSize = 14.sp, color = Color.Black) },
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
fun WorkerProfileStatCard(label: String, value: String, modifier: Modifier = Modifier) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(14.dp),
        color = Color.White
    ) {
        Column(
            modifier = Modifier.padding(12.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = value,
                fontSize = 15.sp,
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
fun WorkerProfileOptionItem(
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

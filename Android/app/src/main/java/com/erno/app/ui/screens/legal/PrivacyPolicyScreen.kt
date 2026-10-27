package com.erno.app.ui.screens.legal

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.erno.app.ui.theme.ErnoGreen

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PrivacyPolicyScreen(
    onBackClick: () -> Unit
) {
    val scrollState = rememberScrollState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Privacy Policy", fontWeight = FontWeight.Bold, color = Color.Black) },
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
        containerColor = Color.White
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(scrollState)
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text(
                text = "Effective Date: October 24, 2023\nLast Updated: May 20, 2024",
                fontSize = 12.sp,
                color = Color.Gray
            )

            SectionTitle("A. Introduction")
            BodyText("Errno operates the ERRNO mobile application and platform (\"Platform\"), connecting shopkeepers and business owners (\"Shopkeepers\") with workers (\"Workers\") for on-demand workforce needs. This Privacy Policy explains how we collect, use, and protect your information.")

            SectionTitle("B. Information We Collect")
            BodyText("1. Personal Information: Full name, mobile number (+91 9971439107 / support.errno@gmail.com), email address, and profile details.\n" +
                    "2. Account Information: Login credentials, OTP verification data, and role selection (Shopkeeper/Worker).\n" +
                    "3. Location Information: Precise GPS and approximate location data when using the app to browse nearby jobs or calculate shift distances. You can control location permissions via your device settings.\n" +
                    "4. Transaction Information: Shift booking details, status, UPI transaction records, and settlement data. Card and banking credentials are handled securely by certified payment gateway partners and are not stored by ERRNO.\n" +
                    "5. Device & Technical Information: IP address, device model, operating system, app version, and diagnostic crash logs.\n" +
                    "6. Communication Information: Customer support interactions, feedback, ratings, and reviews.")

            SectionTitle("C. How We Collect Information")
            BodyText("We collect information directly from you during registration and profile setup, automatically through app usage and location sensors, and securely from third-party payment and OTP service providers.")

            SectionTitle("D. How We Use Information")
            BodyText("• To create and manage user accounts.\n" +
                    "• To connect Shopkeepers and Workers for work opportunities.\n" +
                    "• To process bookings, shift progress ('Ongoing' / 'Completed'), and payments.\n" +
                    "• To send transactional OTPs and service updates.\n" +
                    "• To provide customer support and prevent fraud.")

            SectionTitle("E. Data Sharing & Disclosure")
            BodyText("We do not sell personal data. We share data only with essential cloud infrastructure providers, certified payment gateways, OTP delivery partners, and legal authorities when required by Indian law.")

            SectionTitle("F. Data Security")
            BodyText("We employ industry-standard technical and administrative security measures, including HTTPS encryption in transit and secure database access controls, to safeguard your data.")

            SectionTitle("G. Data Retention")
            BodyText("We retain your account and transaction records as long as your account is active or required for legal and accounting compliance.")

            SectionTitle("H. User Privacy Rights")
            BodyText("You have the right to access, correct, or delete your personal information, and withdraw consent by contacting us at support.errno@gmail.com.")

            SectionTitle("I. Children's Privacy")
            BodyText("ERRNO is strictly intended for individuals aged 18 and above.")

            SectionTitle("J. Grievance Officer & Contact")
            BodyText("Company: Errno Smart Solutions\n" +
                    "Registered Office: New Delhi, India\n" +
                    "Grievance Officer: Mayank Patel\n" +
                    "Support Phone: +91 9971439107\n" +
                    "Email: support.errno@gmail.com")

            Spacer(modifier = Modifier.height(24.dp))
        }
    }
}

@Composable
fun SectionTitle(text: String) {
    Text(
        text = text,
        fontSize = 16.sp,
        fontWeight = FontWeight.Bold,
        color = Color.Black,
        modifier = Modifier.padding(top = 8.dp)
    )
}

@Composable
fun BodyText(text: String) {
    Text(
        text = text,
        fontSize = 14.sp,
        color = Color(0xFF333333),
        lineHeight = 20.sp
    )
}

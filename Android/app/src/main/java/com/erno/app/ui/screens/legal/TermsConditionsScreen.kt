package com.erno.app.ui.screens.legal

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TermsConditionsScreen(
    onBackClick: () -> Unit
) {
    val scrollState = rememberScrollState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Terms & Conditions", fontWeight = FontWeight.Bold, color = Color.Black) },
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

            SectionTitle("A. Acceptance of Terms")
            BodyText("By downloading, registering an account on, or using ERRNO, you agree to be bound by these Terms & Conditions and our Privacy Policy.")

            SectionTitle("B. Description of Services")
            BodyText("ERRNO is a technology marketplace platform connecting Shopkeepers with Workers. ERRNO is not an employer or labor contractor; employment or working arrangements are formed directly between Shopkeepers and Workers.")

            SectionTitle("C. Eligibility & Account Security")
            BodyText("Users must be at least 18 years of age with legal capacity. You are responsible for maintaining account security and OTP confidentiality. Contact support.errno@gmail.com or +91 9971439107 immediately for any unauthorized activity.")

            SectionTitle("D. Shopkeeper & Worker Responsibilities")
            BodyText("• Shopkeepers must provide accurate job details, fair treatment, and timely payments upon shift completion.\n" +
                    "• Workers must maintain accurate profiles, honor accepted shifts punctually, and maintain professional conduct.")

            SectionTitle("E. Prohibited Conduct")
            BodyText("Users shall not create fake accounts, post fraudulent jobs, harass other users, use automated scraping tools, or violate applicable laws.")

            SectionTitle("F. Payments, Cancellations & Refunds")
            BodyText("Transactions are processed via secure payment gateways. Cancellations must be made according to platform guidelines; repeated no-shows may lead to account penalties.")

            SectionTitle("G. Limitation of Liability")
            BodyText("ERRNO provides the platform on an 'AS IS' basis and shall not be liable for indirect damages or disputes arising between Shopkeepers and Workers.")

            SectionTitle("H. Governing Law & Jurisdiction")
            BodyText("These Terms are governed by the laws of India. Courts in New Delhi, India shall have exclusive jurisdiction.")

            SectionTitle("I. Contact Information")
            BodyText("Errno Smart Solutions\n" +
                    "Support Phone: +91 9971439107\n" +
                    "Email: support.errno@gmail.com\n" +
                    "Registered Office: New Delhi, India")

            Spacer(modifier = Modifier.height(24.dp))
        }
    }
}

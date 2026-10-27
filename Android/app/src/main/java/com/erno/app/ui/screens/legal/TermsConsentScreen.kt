package com.erno.app.ui.screens.legal

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.ClickableText
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.erno.app.ui.components.ErnoLogo
import com.erno.app.ui.theme.ErnoGreen
import com.erno.app.ui.theme.ErnoTextSecondary

@Composable
fun TermsConsentScreen(
    onAgreeClick: () -> Unit,
    onTermsClick: () -> Unit,
    onPrivacyClick: () -> Unit
) {
    var isChecked by remember { mutableStateOf(false) }
    val linkColor = Color(0xFF11382A)

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = Color.White
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .statusBarsPadding()
                .navigationBarsPadding()
                .padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.SpaceBetween
        ) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                modifier = Modifier.padding(top = 32.dp)
            ) {
                ErnoLogo(modifier = Modifier.height(40.dp))
                Spacer(modifier = Modifier.height(32.dp))
                
                Text(
                    text = "Welcome to ERRNO",
                    fontSize = 26.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.Black,
                    textAlign = TextAlign.Center
                )
                
                Spacer(modifier = Modifier.height(12.dp))
                
                Text(
                    text = "Before getting started and accessing the platform, please review and accept our Terms of Service and Privacy Policy.",
                    fontSize = 14.sp,
                    color = ErnoTextSecondary,
                    textAlign = TextAlign.Center,
                    lineHeight = 20.sp
                )
            }

            // Middle graphic/card summary
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFFF8F9FA))
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text(
                        text = "Why we require this:",
                        fontWeight = FontWeight.Bold,
                        fontSize = 14.sp,
                        color = Color.Black
                    )
                    Text(
                        text = "• Secure connection between Shopkeepers and Workers.\n• Transparent shift management and UPI payment settlements.\n• Data privacy protection according to Indian regulations.",
                        fontSize = 13.sp,
                        color = Color(0xFF444444),
                        lineHeight = 18.sp
                    )
                }
            }

            // Checkbox and Agreement section
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(16.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .clickable { isChecked = !isChecked },
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Checkbox(
                        checked = isChecked,
                        onCheckedChange = { isChecked = it },
                        colors = CheckboxDefaults.colors(checkedColor = ErnoGreen)
                    )
                    Spacer(modifier = Modifier.width(8.dp))

                    val agreementText = buildAnnotatedString {
                        append("I agree to the ")
                        pushStringAnnotation(tag = "TERMS", annotation = "terms")
                        withStyle(SpanStyle(color = linkColor, fontWeight = FontWeight.Bold, textDecoration = TextDecoration.Underline)) {
                            append("Terms of Service")
                        }
                        pop()
                        append(" and ")
                        pushStringAnnotation(tag = "PRIVACY", annotation = "privacy")
                        withStyle(SpanStyle(color = linkColor, fontWeight = FontWeight.Bold, textDecoration = TextDecoration.Underline)) {
                            append("Privacy Policy")
                        }
                        pop()
                    }

                    ClickableText(
                        text = agreementText,
                        style = TextStyle(fontSize = 13.sp, color = Color.Black),
                        onClick = { offset ->
                            agreementText.getStringAnnotations(tag = "TERMS", start = offset, end = offset).firstOrNull()?.let {
                                onTermsClick()
                            }
                            agreementText.getStringAnnotations(tag = "PRIVACY", start = offset, end = offset).firstOrNull()?.let {
                                onPrivacyClick()
                            }
                        },
                        modifier = Modifier.weight(1f)
                    )
                }

                Button(
                    onClick = onAgreeClick,
                    enabled = isChecked,
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(52.dp),
                    colors = ButtonDefaults.buttonColors(
                        containerColor = ErnoGreen,
                        disabledContainerColor = Color(0xFFE0E0E0)
                    ),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Text(
                        text = "Agree & Continue",
                        fontSize = 16.sp,
                        fontWeight = FontWeight.Bold,
                        color = if (isChecked) Color.White else Color.Gray
                    )
                }
            }
        }
    }
}

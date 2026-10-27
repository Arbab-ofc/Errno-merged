package com.erno.app.ui.screens.role

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.ClickableText
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
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
import com.erno.app.ui.theme.ErnoLime
import com.erno.app.ui.theme.ErnoTextSecondary

enum class Role(val title: String, val description: String, val icon: ImageVector) {
    SHOP_OWNER("Shop Owner", "Hire workers for your store", Icons.Default.Storefront),
    WORKER("Worker", "Find daily wage work easily", Icons.Default.Construction)
}

@Composable
fun RoleSelectionScreen(
    onShopkeeperClick: () -> Unit,
    onWorkerClick: () -> Unit,
    onCreateAccount: () -> Unit = {},
    onTermsClick: () -> Unit = {},
    onPrivacyClick: () -> Unit = {}
) {
    var selectedRole by remember { mutableStateOf(Role.SHOP_OWNER) }
    val darkLinkColor = Color(0xFF11382A) // High contrast dark color for text links only
    val scrollState = rememberScrollState()

    Surface(
        modifier = Modifier.fillMaxSize(),
        color = Color.White
    ) {
        Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.TopCenter
        ) {
            Column(
                modifier = Modifier
                    .widthIn(max = 600.dp) // Responsive tablet & landscape max-width constraint
                    .fillMaxHeight()
                    .verticalScroll(scrollState)
                    .statusBarsPadding()
                    .padding(horizontal = 24.dp, vertical = 16.dp),
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                // Official Logo - Centered
                ErnoLogo(modifier = Modifier.height(32.dp))

                Spacer(modifier = Modifier.height(24.dp))

                // Welcome Text
                Text(
                    text = buildAnnotatedString {
                        append("Welcome to ")
                        withStyle(SpanStyle(color = ErnoLime, fontWeight = FontWeight.Bold)) {
                            append("ERRNO")
                        }
                    },
                    fontSize = 26.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.Black
                )
                
                Spacer(modifier = Modifier.height(8.dp))
                
                Text(
                    text = "On-demand workforce platform for work-based jobs.",
                    fontSize = 14.sp,
                    color = ErnoTextSecondary,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(horizontal = 20.dp)
                )

                Spacer(modifier = Modifier.height(24.dp))

                // Illustration Placeholder
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(140.dp)
                        .background(Color(0xFFF1F8E9), RoundedCornerShape(20.dp)),
                    contentAlignment = Alignment.Center
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(
                            imageVector = if (selectedRole == Role.SHOP_OWNER) Icons.Default.Storefront else Icons.Default.Person,
                            contentDescription = null,
                            modifier = Modifier.size(60.dp),
                            tint = ErnoLime.copy(alpha = 0.6f)
                        )
                    }
                }

                Spacer(modifier = Modifier.height(24.dp))

                Text(
                    text = "Login as",
                    modifier = Modifier.align(Alignment.Start),
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Bold,
                    color = Color.Black
                )

                Spacer(modifier = Modifier.height(12.dp))

                // Roles Row
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(16.dp)
                ) {
                    Role.entries.forEach { role ->
                        RoleCard(
                            role = role,
                            isSelected = selectedRole == role,
                            modifier = Modifier.weight(1f)
                        ) {
                            selectedRole = role
                        }
                    }
                }

                Spacer(modifier = Modifier.height(28.dp))

                // Continue Button
                Button(
                    onClick = {
                        when (selectedRole) {
                            Role.SHOP_OWNER -> onShopkeeperClick()
                            Role.WORKER -> onWorkerClick()
                        }
                    },
                    modifier = Modifier
                        .fillMaxWidth()
                        .height(54.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = ErnoLime),
                    shape = RoundedCornerShape(14.dp),
                    elevation = ButtonDefaults.buttonElevation(defaultElevation = 0.dp)
                ) {
                    Text(
                        text = "Continue",
                        color = Color.Black,
                        fontWeight = FontWeight.Bold,
                        fontSize = 16.sp
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))

                // 1. Create Account Link
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.clickable { onCreateAccount() }
                ) {
                    Text(
                        text = "New to ERRNO? ",
                        fontSize = 14.sp,
                        color = Color.Black
                    )
                    Text(
                        text = "Create an account",
                        color = darkLinkColor,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.ExtraBold,
                        textDecoration = TextDecoration.Underline
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))

                // Safety Info
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.Center,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Icon(
                        imageVector = Icons.Default.Shield,
                        contentDescription = null,
                        modifier = Modifier.size(16.dp),
                        tint = Color.Gray
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = "Your number is safe with us",
                        fontSize = 12.sp,
                        color = Color.Gray
                    )
                }

                Spacer(modifier = Modifier.height(16.dp))

                // 2 & 3. Terms of Service and Privacy Policy Links
                val policyText = buildAnnotatedString {
                    append("By continuing, you agree to our ")
                    pushStringAnnotation(tag = "TERMS", annotation = "terms")
                    withStyle(SpanStyle(color = darkLinkColor, fontWeight = FontWeight.ExtraBold, textDecoration = TextDecoration.Underline)) {
                        append("Terms of Service")
                    }
                    pop()
                    append(" and ")
                    pushStringAnnotation(tag = "PRIVACY", annotation = "privacy")
                    withStyle(SpanStyle(color = darkLinkColor, fontWeight = FontWeight.ExtraBold, textDecoration = TextDecoration.Underline)) {
                        append("Privacy Policy")
                    }
                    pop()
                }

                ClickableText(
                    text = policyText,
                    style = TextStyle(fontSize = 12.sp, color = Color.Gray, textAlign = TextAlign.Center),
                    onClick = { offset ->
                        policyText.getStringAnnotations(tag = "TERMS", start = offset, end = offset).firstOrNull()?.let {
                            onTermsClick()
                        }
                        policyText.getStringAnnotations(tag = "PRIVACY", start = offset, end = offset).firstOrNull()?.let {
                            onPrivacyClick()
                        }
                    },
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 8.dp)
                )
                
                Spacer(modifier = Modifier.navigationBarsPadding())
            }
        }
    }
}

@Composable
fun RoleCard(
    role: Role,
    isSelected: Boolean,
    modifier: Modifier = Modifier,
    onClick: () -> Unit
) {
    val borderColor = if (isSelected) ErnoLime else Color(0xFFF0F0F0)
    val titleColor = if (isSelected) ErnoLime else Color.Black
    val backgroundColor = if (isSelected) Color.White else Color(0xFFFAFAFA)

    Surface(
        onClick = onClick,
        modifier = modifier
            .height(120.dp)
            .border(
                width = if (isSelected) 2.dp else 1.dp,
                color = borderColor,
                shape = RoundedCornerShape(16.dp)
            ),
        shape = RoundedCornerShape(16.dp),
        color = backgroundColor,
        shadowElevation = if (isSelected) 2.dp else 0.dp
    ) {
        Box(modifier = Modifier.padding(8.dp)) {
            if (isSelected) {
                Icon(
                    imageVector = Icons.Default.CheckCircle,
                    contentDescription = null,
                    tint = ErnoLime,
                    modifier = Modifier
                        .size(18.dp)
                        .align(Alignment.TopEnd)
                )
            }

            Column(
                modifier = Modifier.fillMaxSize(),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center
            ) {
                Icon(
                    imageVector = role.icon,
                    contentDescription = null,
                    tint = if (isSelected) ErnoLime else Color.Gray,
                    modifier = Modifier.size(30.dp)
                )
                Spacer(modifier = Modifier.height(6.dp))
                Text(
                    text = role.title,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold,
                    color = titleColor,
                    textAlign = TextAlign.Center
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = role.description,
                    fontSize = 10.sp,
                    color = Color.Gray,
                    textAlign = TextAlign.Center,
                    lineHeight = 12.sp
                )
            }
        }
    }
}

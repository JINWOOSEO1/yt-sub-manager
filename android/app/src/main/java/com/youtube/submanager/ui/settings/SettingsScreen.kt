package com.youtube.submanager.ui.settings

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import kotlin.math.roundToInt

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    onBack: () -> Unit,
    onLogout: () -> Unit,
    viewModel: SettingsViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    val snackbarHostState = remember { SnackbarHostState() }

    LaunchedEffect(uiState.error) {
        uiState.error?.let {
            snackbarHostState.showSnackbar(it)
            viewModel.clearError()
        }
    }

    LaunchedEffect(uiState.saveSuccess) {
        if (uiState.saveSuccess) {
            snackbarHostState.showSnackbar("저장 완료")
            viewModel.clearSaveSuccess()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("설정") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "뒤로")
                    }
                }
            )
        },
        snackbarHost = { SnackbarHost(snackbarHostState) }
    ) { paddingValues ->
        if (uiState.isLoading) {
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues),
                contentAlignment = Alignment.Center
            ) {
                CircularProgressIndicator()
            }
        } else {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .padding(paddingValues)
                    .padding(16.dp)
            ) {
                uiState.preferences?.let { prefs ->
                    // Auto-delete days
                    Text(
                        "자동 삭제",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                    Spacer(modifier = Modifier.height(8.dp))

                    var deleteDays by remember {
                        mutableFloatStateOf(prefs.auto_delete_days.coerceAtMost(14).toFloat())
                    }
                    Text("${deleteDays.roundToInt()}일 이후 영상 자동 삭제")
                    Slider(
                        value = deleteDays,
                        onValueChange = { deleteDays = it },
                        onValueChangeFinished = {
                            viewModel.updateAutoDeleteDays(deleteDays.roundToInt())
                        },
                        valueRange = 1f..14f,
                        steps = 12
                    )

                    Spacer(modifier = Modifier.height(24.dp))

                    // Polling interval
                    Text(
                        "폴링 간격",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                    Spacer(modifier = Modifier.height(8.dp))

                    var pollingMin by remember { mutableFloatStateOf(prefs.polling_interval_min.toFloat()) }
                    Text("${pollingMin.roundToInt()}분마다 새 영상 확인")
                    Slider(
                        value = pollingMin,
                        onValueChange = { pollingMin = it },
                        onValueChangeFinished = {
                            viewModel.updatePollingInterval(pollingMin.roundToInt())
                        },
                        valueRange = 5f..60f,
                        steps = 10
                    )

                    Spacer(modifier = Modifier.height(24.dp))

                    // Notifications
                    Text(
                        "알림",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                    Spacer(modifier = Modifier.height(8.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Text("새 영상 알림")
                        Switch(
                            checked = prefs.notification_enabled,
                            onCheckedChange = { viewModel.updateNotificationEnabled(it) }
                        )
                    }
                }

                Spacer(modifier = Modifier.weight(1f))

                // Logout
                OutlinedButton(
                    onClick = onLogout,
                    modifier = Modifier.fillMaxWidth(),
                    colors = ButtonDefaults.outlinedButtonColors(
                        contentColor = MaterialTheme.colorScheme.error
                    )
                ) {
                    Text("로그아웃")
                }
            }
        }
    }
}

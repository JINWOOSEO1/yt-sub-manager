package com.youtube.submanager.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.youtube.submanager.data.repository.AuthRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AuthUiState(
    val isLoading: Boolean = false,
    val isLoggedIn: Boolean = false,
    val error: String? = null
)

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val authRepository: AuthRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(AuthUiState())
    val uiState: StateFlow<AuthUiState> = _uiState

    init {
        _uiState.value = AuthUiState(isLoggedIn = authRepository.isLoggedIn())
    }

    fun onGoogleSignInResult(serverAuthCode: String?) {
        if (serverAuthCode == null) {
            _uiState.value = _uiState.value.copy(error = "Google 로그인에 실패했습니다.")
            return
        }

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            val result = authRepository.login(serverAuthCode)
            _uiState.value = if (result.isSuccess) {
                _uiState.value.copy(isLoading = false, isLoggedIn = true)
            } else {
                _uiState.value.copy(
                    isLoading = false,
                    error = result.exceptionOrNull()?.message ?: "로그인 실패"
                )
            }
        }
    }

    fun logout() {
        viewModelScope.launch {
            authRepository.logout()
            _uiState.value = AuthUiState(isLoggedIn = false)
        }
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }
}

package com.youtube.submanager.ui.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.youtube.submanager.data.model.Preferences
import com.youtube.submanager.data.model.PreferencesUpdate
import com.youtube.submanager.data.repository.VideoRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SettingsUiState(
    val preferences: Preferences? = null,
    val isLoading: Boolean = false,
    val isSaving: Boolean = false,
    val error: String? = null,
    val saveSuccess: Boolean = false
)

@HiltViewModel
class SettingsViewModel @Inject constructor(
    private val repository: VideoRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(SettingsUiState())
    val uiState: StateFlow<SettingsUiState> = _uiState

    init {
        loadPreferences()
    }

    private fun loadPreferences() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            try {
                val prefs = repository.getPreferences()
                _uiState.value = _uiState.value.copy(
                    preferences = prefs,
                    isLoading = false
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message
                )
            }
        }
    }

    fun updateAutoDeleteDays(days: Int) {
        savePreferences(PreferencesUpdate(auto_delete_days = days))
    }

    fun updateNotificationEnabled(enabled: Boolean) {
        savePreferences(PreferencesUpdate(notification_enabled = enabled))
    }

    fun updatePollingInterval(minutes: Int) {
        savePreferences(PreferencesUpdate(polling_interval_min = minutes))
    }

    fun clearError() {
        _uiState.value = _uiState.value.copy(error = null)
    }

    fun clearSaveSuccess() {
        _uiState.value = _uiState.value.copy(saveSuccess = false)
    }

    private fun savePreferences(update: PreferencesUpdate) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isSaving = true, saveSuccess = false)
            try {
                val prefs = repository.updatePreferences(update)
                _uiState.value = _uiState.value.copy(
                    preferences = prefs,
                    isSaving = false,
                    saveSuccess = true
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isSaving = false,
                    error = e.message
                )
            }
        }
    }
}

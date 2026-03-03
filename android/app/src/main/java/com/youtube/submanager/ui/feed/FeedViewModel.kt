package com.youtube.submanager.ui.feed

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.youtube.submanager.data.model.Channel
import com.youtube.submanager.data.model.Video
import com.youtube.submanager.data.repository.VideoRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

private const val SYNC_POLL_INTERVAL_MS = 500L
private const val SYNC_POLL_ATTEMPTS = 90

data class DismissedVideoInfo(
    val video: Video,
    val index: Int
)

data class FeedUiState(
    val videos: List<Video> = emptyList(),
    val channels: List<Channel> = emptyList(),
    val selectedChannel: Channel? = null,
    val isLoading: Boolean = false,
    val isRefreshing: Boolean = false,
    val isSyncing: Boolean = false,
    val error: String? = null,
    val currentPage: Int = 1,
    val hasMore: Boolean = true,
    val totalCount: Int = 0,
    val lastDismissed: DismissedVideoInfo? = null
) {
    val canUndo: Boolean get() = lastDismissed != null
}

@HiltViewModel
class FeedViewModel @Inject constructor(
    private val repository: VideoRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(FeedUiState())
    val uiState: StateFlow<FeedUiState> = _uiState

    init {
        loadVideos()
        loadChannels()
    }

    fun loadVideos() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, error = null)
            try {
                val channelId = _uiState.value.selectedChannel?.id
                val response = repository.getVideos(status = "new", page = 1, channelId = channelId)
                _uiState.value = _uiState.value.copy(
                    videos = response.items,
                    isLoading = false,
                    currentPage = 1,
                    hasMore = response.items.size < response.total,
                    totalCount = response.total
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isLoading = false,
                    error = e.message ?: "영상을 불러오지 못했습니다"
                )
            }
        }
    }

    fun loadMore() {
        val state = _uiState.value
        if (state.isLoading || !state.hasMore) return

        viewModelScope.launch {
            val nextPage = state.currentPage + 1
            try {
                val channelId = state.selectedChannel?.id
                val response = repository.getVideos(status = "new", page = nextPage, channelId = channelId)
                _uiState.value = state.copy(
                    videos = state.videos + response.items,
                    currentPage = nextPage,
                    hasMore = (state.videos.size + response.items.size) < response.total
                )
            } catch (e: Exception) {
                _uiState.value = state.copy(error = e.message)
            }
        }
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isRefreshing = true, error = null)
            try {
                val channelId = _uiState.value.selectedChannel?.id
                val response = repository.getVideos(status = "new", page = 1, channelId = channelId)
                _uiState.value = _uiState.value.copy(
                    videos = response.items,
                    isRefreshing = false,
                    currentPage = 1,
                    hasMore = response.items.size < response.total,
                    totalCount = response.total
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isRefreshing = false,
                    error = e.message
                )
            }
        }
    }

    fun dismissVideo(videoId: Int) {
        viewModelScope.launch {
            try {
                val state = _uiState.value
                val index = state.videos.indexOfFirst { it.id == videoId }
                val video = if (index >= 0) state.videos[index] else null

                repository.dismissVideo(videoId)

                _uiState.value = state.copy(
                    videos = state.videos.filter { it.id != videoId },
                    totalCount = state.totalCount - 1,
                    lastDismissed = video?.let { DismissedVideoInfo(it, index) }
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = "Dismiss 실패: ${e.message}")
            }
        }
    }

    fun undoDismiss() {
        val state = _uiState.value
        val dismissed = state.lastDismissed ?: return
        viewModelScope.launch {
            try {
                repository.restoreVideo(dismissed.video.id)
                val newList = state.videos.toMutableList()
                val insertIndex = dismissed.index.coerceAtMost(newList.size)
                newList.add(insertIndex, dismissed.video)
                _uiState.value = state.copy(
                    videos = newList,
                    totalCount = state.totalCount + 1,
                    lastDismissed = null
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = "복구 실패: ${e.message}")
            }
        }
    }

    fun markWatched(videoId: Int) {
        viewModelScope.launch {
            try {
                repository.markWatched(videoId)
                _uiState.value = _uiState.value.copy(
                    videos = _uiState.value.videos.filter { it.id != videoId },
                    totalCount = _uiState.value.totalCount - 1
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(error = e.message)
            }
        }
    }

    fun setChannelFilter(channel: Channel?) {
        _uiState.value = _uiState.value.copy(selectedChannel = channel)
        loadVideos()
    }

    fun loadChannels() {
        viewModelScope.launch {
            try {
                val channels = repository.getChannels()
                _uiState.value = _uiState.value.copy(channels = channels)
            } catch (_: Exception) {
                // Channel list is supplementary, don't show error
            }
        }
    }

    fun syncChannels() {
        if (_uiState.value.isSyncing) return

        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isSyncing = true, error = null)
            try {
                repository.syncChannels()
                val finalStatus = waitForSyncCompletion()
                if (finalStatus.state == "failed") {
                    throw IllegalStateException(finalStatus.error ?: finalStatus.message)
                }

                val channels = repository.getChannels()
                val channelId = _uiState.value.selectedChannel?.id
                val response = repository.getVideos(
                    status = "new",
                    page = 1,
                    channelId = channelId
                )
                _uiState.value = _uiState.value.copy(
                    channels = channels,
                    videos = response.items,
                    isSyncing = false,
                    currentPage = 1,
                    hasMore = response.items.size < response.total,
                    totalCount = response.total
                )
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(
                    isSyncing = false,
                    error = "동기화 실패: ${e.message}"
                )
            }
        }
    }

    private suspend fun waitForSyncCompletion(): com.youtube.submanager.data.model.SyncResponse {
        repeat(SYNC_POLL_ATTEMPTS) {
            val status = repository.getSyncStatus()
            if (status.state == "succeeded" || status.state == "failed") {
                return status
            }
            delay(SYNC_POLL_INTERVAL_MS)
        }

        throw IllegalStateException("동기화가 제한 시간 안에 끝나지 않았습니다")
    }
}

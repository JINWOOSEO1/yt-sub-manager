package com.youtube.submanager.data.repository

import com.youtube.submanager.data.api.ApiService
import com.youtube.submanager.data.model.*
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class VideoRepository @Inject constructor(
    private val api: ApiService
) {
    suspend fun getVideos(
        status: String = "new",
        page: Int = 1,
        perPage: Int = 20,
        channelId: Int? = null
    ): VideoListResponse = api.getVideos(status, page, perPage, channelId)

    suspend fun dismissVideo(videoId: Int) = api.dismissVideo(videoId)

    suspend fun markWatched(videoId: Int) = api.markWatched(videoId)

    suspend fun restoreVideo(videoId: Int) = api.restoreVideo(videoId)

    suspend fun dismissBatch(videoIds: List<Int>) =
        api.dismissBatch(DismissBatchRequest(videoIds))

    suspend fun getStats() = api.getVideoStats()

    suspend fun getChannels() = api.getChannels()

    suspend fun syncChannels() = api.syncChannels()

    suspend fun getSyncStatus() = api.getSyncStatus()

    suspend fun removeChannel(channelId: Int) = api.removeChannel(channelId)

    suspend fun getPreferences() = api.getPreferences()

    suspend fun updatePreferences(update: PreferencesUpdate) =
        api.updatePreferences(update)
}

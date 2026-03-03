package com.youtube.submanager.data.api

import com.youtube.submanager.data.model.*
import retrofit2.http.*

interface ApiService {

    // Auth
    @POST("api/v1/auth/google")
    suspend fun googleAuth(@Body body: GoogleAuthRequest): TokenResponse

    @POST("api/v1/auth/fcm-token")
    suspend fun registerFcmToken(@Body body: FcmTokenRequest): MessageResponse

    @POST("api/v1/auth/refresh")
    suspend fun refreshToken(): TokenResponse

    // Videos
    @GET("api/v1/videos")
    suspend fun getVideos(
        @Query("status") status: String = "new",
        @Query("page") page: Int = 1,
        @Query("per_page") perPage: Int = 20,
        @Query("channel_id") channelId: Int? = null
    ): VideoListResponse

    @PATCH("api/v1/videos/{videoId}/dismiss")
    suspend fun dismissVideo(@Path("videoId") videoId: Int): MessageResponse

    @PATCH("api/v1/videos/{videoId}/watched")
    suspend fun markWatched(@Path("videoId") videoId: Int): MessageResponse

    @PATCH("api/v1/videos/{videoId}/restore")
    suspend fun restoreVideo(@Path("videoId") videoId: Int): MessageResponse

    @POST("api/v1/videos/dismiss-batch")
    suspend fun dismissBatch(@Body body: DismissBatchRequest): MessageResponse

    @GET("api/v1/videos/stats")
    suspend fun getVideoStats(): VideoStats

    // Channels
    @GET("api/v1/channels")
    suspend fun getChannels(): List<Channel>

    @POST("api/v1/channels/sync")
    suspend fun syncChannels(): SyncResponse

    @GET("api/v1/channels/sync-status")
    suspend fun getSyncStatus(): SyncResponse

    @DELETE("api/v1/channels/{channelId}")
    suspend fun removeChannel(@Path("channelId") channelId: Int): MessageResponse

    // Preferences
    @GET("api/v1/preferences")
    suspend fun getPreferences(): Preferences

    @PUT("api/v1/preferences")
    suspend fun updatePreferences(@Body body: PreferencesUpdate): Preferences
}

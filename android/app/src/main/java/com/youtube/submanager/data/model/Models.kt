package com.youtube.submanager.data.model

import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class Channel(
    val id: Int,
    val youtube_channel_id: String,
    val title: String,
    val thumbnail_url: String?
)

@JsonClass(generateAdapter = true)
data class Video(
    val id: Int,
    val youtube_video_id: String,
    val title: String,
    val thumbnail_url: String?,
    val published_at: String,
    val duration: String?,
    val status: String,
    val channel: Channel
)

@JsonClass(generateAdapter = true)
data class VideoListResponse(
    val items: List<Video>,
    val total: Int,
    val page: Int,
    val per_page: Int
)

@JsonClass(generateAdapter = true)
data class VideoStats(
    val new: Int,
    val dismissed: Int,
    val watched: Int,
    val total: Int
)

@JsonClass(generateAdapter = true)
data class DismissBatchRequest(
    val video_ids: List<Int>
)

@JsonClass(generateAdapter = true)
data class Preferences(
    val auto_delete_days: Int,
    val polling_interval_min: Int,
    val notification_enabled: Boolean
)

@JsonClass(generateAdapter = true)
data class PreferencesUpdate(
    val auto_delete_days: Int? = null,
    val polling_interval_min: Int? = null,
    val notification_enabled: Boolean? = null
)

@JsonClass(generateAdapter = true)
data class FcmTokenRequest(
    val fcm_token: String
)

@JsonClass(generateAdapter = true)
data class GoogleAuthRequest(
    val auth_code: String
)

@JsonClass(generateAdapter = true)
data class TokenResponse(
    val access_token: String,
    val token_type: String
)

@JsonClass(generateAdapter = true)
data class MessageResponse(
    val message: String
)

@JsonClass(generateAdapter = true)
data class SyncResponse(
    val state: String,
    val message: String,
    val started_at: String? = null,
    val finished_at: String? = null,
    val channel_count: Int? = null,
    val error: String? = null
)

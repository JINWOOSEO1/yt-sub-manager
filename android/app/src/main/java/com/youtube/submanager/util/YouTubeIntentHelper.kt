package com.youtube.submanager.util

import android.content.Context
import android.content.Intent
import android.net.Uri

object YouTubeIntentHelper {
    fun openVideo(context: Context, videoId: String) {
        // Try to open in YouTube app first
        val appIntent = Intent(Intent.ACTION_VIEW, Uri.parse("vnd.youtube:$videoId"))
        if (appIntent.resolveActivity(context.packageManager) != null) {
            context.startActivity(appIntent)
        } else {
            // Fallback to browser
            val webIntent = Intent(
                Intent.ACTION_VIEW,
                Uri.parse("https://www.youtube.com/watch?v=$videoId")
            )
            context.startActivity(webIntent)
        }
    }
}

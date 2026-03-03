package com.youtube.submanager.ui.theme

import android.os.Build
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext

private val LightColorScheme = lightColorScheme(
    primary = Color(0xFFCC0000),           // YouTube red
    onPrimary = Color.White,
    primaryContainer = Color(0xFFFFDAD5),
    secondary = Color(0xFF282828),
    surface = Color.White,
    background = Color(0xFFF9F9F9),
)

private val DarkColorScheme = darkColorScheme(
    primary = Color(0xFFFF4E45),
    onPrimary = Color.White,
    primaryContainer = Color(0xFF930006),
    secondary = Color(0xFFAAAAAA),
    surface = Color(0xFF181818),
    background = Color(0xFF0F0F0F),
)

@Composable
fun YTSubManagerTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit
) {
    val colorScheme = when {
        Build.VERSION.SDK_INT >= Build.VERSION_CODES.S -> {
            val context = LocalContext.current
            if (darkTheme) dynamicDarkColorScheme(context)
            else dynamicLightColorScheme(context)
        }
        darkTheme -> DarkColorScheme
        else -> LightColorScheme
    }

    MaterialTheme(
        colorScheme = colorScheme,
        content = content
    )
}

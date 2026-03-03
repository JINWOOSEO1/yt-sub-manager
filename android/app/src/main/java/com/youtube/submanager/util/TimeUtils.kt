package com.youtube.submanager.util

import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.time.format.DateTimeParseException
import java.time.temporal.ChronoUnit

private val koreaZoneId: ZoneId = ZoneId.of("Asia/Seoul")

fun formatRelativeTime(isoString: String): String {
    val publishedDate = parsePublishedDateInKorea(isoString) ?: return isoString
    val todayInKorea = LocalDate.now(koreaZoneId)
    val years = ChronoUnit.YEARS.between(publishedDate, todayInKorea)
    val months = ChronoUnit.MONTHS.between(publishedDate, todayInKorea)
    val days = ChronoUnit.DAYS.between(publishedDate, todayInKorea)

    return when {
        !publishedDate.isBefore(todayInKorea) -> "오늘"
        years >= 1 -> "${years}년전"
        months >= 1 -> "${months}달전"
        days >= 7 -> "${days / 7}주전"
        else -> "${days}일전"
    }
}

private fun parsePublishedDateInKorea(isoString: String): LocalDate? {
    return try {
        OffsetDateTime.parse(isoString, DateTimeFormatter.ISO_DATE_TIME)
            .atZoneSameInstant(koreaZoneId)
            .toLocalDate()
    } catch (_: DateTimeParseException) {
        try {
            Instant.parse(isoString)
                .atZone(koreaZoneId)
                .toLocalDate()
        } catch (_: DateTimeParseException) {
            try {
                LocalDateTime.parse(isoString, DateTimeFormatter.ISO_DATE_TIME)
                    .atOffset(ZoneOffset.UTC)
                    .atZoneSameInstant(koreaZoneId)
                    .toLocalDate()
            } catch (_: DateTimeParseException) {
                null
            }
        }
    }
}

package com.youtube.submanager.ui.feed

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material.ExperimentalMaterialApi
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material.pullrefresh.PullRefreshIndicator
import androidx.compose.material.pullrefresh.pullRefresh
import androidx.compose.material.pullrefresh.rememberPullRefreshState
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import coil.compose.AsyncImage
import com.youtube.submanager.data.model.Channel
import com.youtube.submanager.data.model.Video
import com.youtube.submanager.util.YouTubeIntentHelper
import com.youtube.submanager.util.formatRelativeTime

private const val DISMISS_THRESHOLD_FRACTION = 0.9f

@OptIn(ExperimentalMaterial3Api::class, ExperimentalMaterialApi::class)
@Composable
fun FeedScreen(
    onNavigateToSettings: () -> Unit,
    viewModel: FeedViewModel = hiltViewModel()
) {
    val uiState by viewModel.uiState.collectAsState()
    val context = LocalContext.current
    val listState = rememberLazyListState()

    // Pull-to-refresh
    val pullRefreshState = rememberPullRefreshState(
        refreshing = uiState.isRefreshing,
        onRefresh = { viewModel.refresh() }
    )

    // Load more when scrolling near the end
    val shouldLoadMore by remember {
        derivedStateOf {
            val lastVisibleItem = listState.layoutInfo.visibleItemsInfo.lastOrNull()?.index ?: 0
            lastVisibleItem >= uiState.videos.size - 3
        }
    }

    LaunchedEffect(shouldLoadMore) {
        if (shouldLoadMore && uiState.hasMore && !uiState.isLoading) {
            viewModel.loadMore()
        }
    }

    // Channel filter state
    var showChannelFilter by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("YT Sub Manager", fontWeight = FontWeight.Bold) },
                actions = {
                    // Channel filter button
                    IconButton(onClick = { showChannelFilter = true }) {
                        Icon(
                            if (uiState.selectedChannel != null) Icons.Default.FilterList
                            else Icons.Default.List,
                            contentDescription = "채널 필터"
                        )
                    }
                    // Rollback button
                    IconButton(
                        onClick = { viewModel.undoDismiss() },
                        enabled = uiState.canUndo
                    ) {
                        Icon(Icons.Default.Replay, contentDescription = "되돌리기")
                    }
                    IconButton(
                        onClick = { viewModel.syncChannels() },
                        enabled = !uiState.isSyncing
                    ) {
                        if (uiState.isSyncing) {
                            CircularProgressIndicator(
                                modifier = Modifier.size(20.dp),
                                strokeWidth = 2.dp
                            )
                        } else {
                            Icon(Icons.Default.Refresh, contentDescription = "동기화")
                        }
                    }
                    IconButton(onClick = onNavigateToSettings) {
                        Icon(Icons.Default.Settings, contentDescription = "설정")
                    }
                }
            )
        }
    ) { paddingValues ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(paddingValues)
                .pullRefresh(pullRefreshState)
        ) {
            when {
                uiState.isLoading && uiState.videos.isEmpty() -> {
                    CircularProgressIndicator(
                        modifier = Modifier.align(Alignment.Center)
                    )
                }
                uiState.error != null && uiState.videos.isEmpty() -> {
                    Column(
                        modifier = Modifier.align(Alignment.Center),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text(uiState.error ?: "", color = MaterialTheme.colorScheme.error)
                        Spacer(modifier = Modifier.height(8.dp))
                        Button(onClick = { viewModel.loadVideos() }) {
                            Text("다시 시도")
                        }
                    }
                }
                uiState.videos.isEmpty() -> {
                    Column(
                        modifier = Modifier.align(Alignment.Center),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Icon(
                            Icons.Default.CheckCircle,
                            contentDescription = null,
                            modifier = Modifier.size(64.dp),
                            tint = MaterialTheme.colorScheme.primary
                        )
                        Spacer(modifier = Modifier.height(16.dp))
                        Text("모든 영상을 확인했습니다!", fontSize = 18.sp)
                        Spacer(modifier = Modifier.height(8.dp))
                        TextButton(
                            onClick = { viewModel.syncChannels() },
                            enabled = !uiState.isSyncing
                        ) {
                            Text("구독 채널 동기화")
                        }
                    }
                }
                else -> {
                    LazyColumn(
                        state = listState,
                        contentPadding = PaddingValues(vertical = 8.dp)
                    ) {
                        items(
                            items = uiState.videos,
                            key = { it.id }
                        ) { video ->
                            SwipeableVideoCard(
                                video = video,
                                onDismiss = { viewModel.dismissVideo(video.id) },
                                onClick = {
                                    YouTubeIntentHelper.openVideo(context, video.youtube_video_id)
                                }
                            )
                        }

                        if (uiState.isLoading && uiState.videos.isNotEmpty()) {
                            item {
                                Box(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(16.dp),
                                    contentAlignment = Alignment.Center
                                ) {
                                    CircularProgressIndicator(
                                        modifier = Modifier.size(24.dp)
                                    )
                                }
                            }
                        }
                    }
                }
            }

            // Pull-to-refresh indicator
            PullRefreshIndicator(
                refreshing = uiState.isRefreshing,
                state = pullRefreshState,
                modifier = Modifier.align(Alignment.TopCenter)
            )
        }

        // Channel filter bottom sheet
        if (showChannelFilter) {
            ChannelFilterSheet(
                channels = uiState.channels,
                selectedChannel = uiState.selectedChannel,
                onSelect = { channel ->
                    viewModel.setChannelFilter(channel)
                    showChannelFilter = false
                },
                onDismiss = { showChannelFilter = false }
            )
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChannelFilterSheet(
    channels: List<Channel>,
    selectedChannel: Channel?,
    onSelect: (Channel?) -> Unit,
    onDismiss: () -> Unit
) {
    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(modifier = Modifier.padding(bottom = 32.dp)) {
            Text(
                "채널 필터",
                fontSize = 18.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp)
            )

            // "All channels" option
            ListItem(
                headlineContent = { Text("전체 채널") },
                leadingContent = {
                    RadioButton(
                        selected = selectedChannel == null,
                        onClick = { onSelect(null) }
                    )
                },
                modifier = Modifier.clickable { onSelect(null) }
            )

            channels.forEach { channel ->
                ListItem(
                    headlineContent = { Text(channel.title) },
                    leadingContent = {
                        RadioButton(
                            selected = selectedChannel?.id == channel.id,
                            onClick = { onSelect(channel) }
                        )
                    },
                    modifier = Modifier.clickable { onSelect(channel) }
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SwipeableVideoCard(
    video: Video,
    onDismiss: () -> Unit,
    onClick: () -> Unit
) {
    val dismissState = rememberSwipeToDismissBoxState(
        positionalThreshold = { distance -> distance * DISMISS_THRESHOLD_FRACTION },
        confirmValueChange = { value ->
            if (value == SwipeToDismissBoxValue.StartToEnd) {
                onDismiss()
                true
            } else {
                false
            }
        }
    )

    SwipeToDismissBox(
        state = dismissState,
        enableDismissFromEndToStart = false,
        backgroundContent = {
            val color by animateColorAsState(
                when (dismissState.targetValue) {
                    SwipeToDismissBoxValue.Settled -> Color.Transparent
                    else -> MaterialTheme.colorScheme.errorContainer
                },
                label = "swipe-bg"
            )
            Box(
                modifier = Modifier
                    .fillMaxSize()
                    .background(color)
                    .padding(horizontal = 20.dp),
                contentAlignment = if (dismissState.targetValue == SwipeToDismissBoxValue.StartToEnd) {
                    Alignment.CenterStart
                } else {
                    Alignment.CenterEnd
                }
            ) {
                Icon(
                    Icons.Default.Delete,
                    contentDescription = "삭제",
                    tint = MaterialTheme.colorScheme.onErrorContainer
                )
            }
        }
    ) {
        VideoCard(video = video, onClick = onClick)
    }
}

@Composable
fun VideoCard(
    video: Video,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 12.dp, vertical = 4.dp)
            .clickable(onClick = onClick),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surface
        ),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(12.dp),
            verticalAlignment = Alignment.Top
        ) {
            // Thumbnail
            AsyncImage(
                model = video.thumbnail_url,
                contentDescription = video.title,
                modifier = Modifier
                    .width(160.dp)
                    .height(90.dp)
                    .clip(MaterialTheme.shapes.small),
                contentScale = ContentScale.Crop
            )

            Spacer(modifier = Modifier.width(12.dp))

            // Video info
            Column(
                modifier = Modifier.weight(1f)
            ) {
                Text(
                    text = video.title,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Medium,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                    lineHeight = 18.sp
                )

                Spacer(modifier = Modifier.height(4.dp))

                Text(
                    text = video.channel.title,
                    fontSize = 12.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )

                Spacer(modifier = Modifier.height(2.dp))

                Text(
                    text = formatRelativeTime(video.published_at),
                    fontSize = 11.sp,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

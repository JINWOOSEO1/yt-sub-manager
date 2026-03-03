plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
    id("com.google.dagger.hilt.android")
    id("com.google.devtools.ksp")
    id("com.google.gms.google-services")
}

android {
    namespace = "com.youtube.submanager"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.youtube.submanager"
        minSdk = 26
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0"

    }

    buildTypes {
        debug {
            buildConfigField("String", "BASE_URL", "\"https://yt-sub-manager.onrender.com\"")
        }
        release {
            buildConfigField("String", "BASE_URL", "\"https://yt-sub-manager.onrender.com\"")
            isMinifyEnabled = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    buildFeatures {
        compose = true
        buildConfig = true
    }
}

dependencies {
    // Compose BOM
    val composeBom = platform("androidx.compose:compose-bom:2024.12.01")
    implementation(composeBom)

    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.ui:ui-tooling-preview")
    implementation("androidx.activity:activity-compose:1.9.3")
    debugImplementation("androidx.compose.ui:ui-tooling")

    // Navigation
    implementation("androidx.navigation:navigation-compose:2.8.5")

    // Lifecycle
    implementation("androidx.lifecycle:lifecycle-runtime-compose:2.8.7")
    implementation("androidx.lifecycle:lifecycle-viewmodel-compose:2.8.7")

    // Hilt DI
    implementation("com.google.dagger:hilt-android:2.53.1")
    ksp("com.google.dagger:hilt-compiler:2.53.1")
    implementation("androidx.hilt:hilt-navigation-compose:1.2.0")

    // Retrofit + Moshi
    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-moshi:2.11.0")
    implementation("com.squareup.moshi:moshi:1.15.2")
    ksp("com.squareup.moshi:moshi-kotlin-codegen:1.15.2")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    // Coil - image loading
    implementation("io.coil-kt:coil-compose:2.7.0")

    // Google Sign-In
    implementation("com.google.android.gms:play-services-auth:21.3.0")

    // Firebase
    implementation(platform("com.google.firebase:firebase-bom:33.7.0"))
    implementation("com.google.firebase:firebase-messaging")

    // DataStore for local preferences
    implementation("androidx.datastore:datastore-preferences:1.1.2")

    // Swipe refresh
    implementation("androidx.compose.material:material:1.7.6")

    // Extended material icons (FilterList, ClearAll, etc.)
    implementation("androidx.compose.material:material-icons-extended:1.7.6")
}

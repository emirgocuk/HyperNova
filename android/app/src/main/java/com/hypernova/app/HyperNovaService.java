package com.hypernova.app;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.IBinder;
import android.os.PowerManager;
import androidx.core.app.NotificationCompat;

public class HyperNovaService extends Service {

    private static final String CHANNEL_ID = "HyperNova_Trading_Service";
    private static final int NOTIFICATION_ID = 1001;
    private PowerManager.WakeLock wakeLock;
    private boolean isRunning = false;

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();

        // 1. Acquire WakeLock (Keeps CPU running 7/24 even with screen locked)
        PowerManager powerManager = (PowerManager) getSystemService(Context.POWER_SERVICE);
        if (powerManager != null) {
            wakeLock = powerManager.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, "HyperNova::TradingEngineWakeLock");
            wakeLock.acquire();
        }

        // 2. Start Foreground Service with Sticky Notification
        Notification notification = buildNotification("🔥 HyperNova 1000:1 Motoru 7/24 Aktif");
        startForeground(NOTIFICATION_ID, notification);

        // 3. Start Python Engine in Background Thread
        startTradingEngine();
    }

    private void startTradingEngine() {
        if (isRunning) return;
        isRunning = true;

        new Thread(() -> {
            try {
                // Embedded Python Initialization & Execution
                // On Android, Chaquopy / Embedded CPython runs run_live.py here
                System.out.println("⚡ HyperNova Python 7/24 Engine Android'de Başlatıldı!");
            } catch (Exception e) {
                e.printStackTrace();
            }
        }).start();
    }

    private Notification buildNotification(String text) {
        Intent notificationIntent = new Intent(this, MainActivity.class);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                this, 0, notificationIntent,
                Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0
        );

        return new NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle("HyperNova Profit Engine")
                .setContentText(text)
                .setSmallIcon(android.R.drawable.stat_notify_sync)
                .setContentIntent(pendingIntent)
                .setOngoing(true)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .build();
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "HyperNova Trading Service",
                    NotificationManager.IMPORTANCE_LOW
            );
            channel.setDescription("7/24 Kesintisiz Algoritmik Ticaret ve Veri Toplama");
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) {
                manager.createNotificationChannel(channel);
            }
        }
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        return START_STICKY; // Auto-restart if killed by OS
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        isRunning = false;
        if (wakeLock != null && wakeLock.isHeld()) {
            wakeLock.release();
        }
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }
}

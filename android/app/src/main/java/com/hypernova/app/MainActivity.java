package com.hypernova.app;

import android.app.AlertDialog;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.view.View;
import android.view.Window;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.FileProvider;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.nio.channels.FileChannel;
import java.util.Locale;

public class MainActivity extends AppCompatActivity implements MarketDataCollector.TelemetryListener {

    private TextView txtStatusBadge;
    private TextView txtDataCount;
    private TextView txtTotalPnl;
    private TextView txtAlphaScore;
    private TextView txtSolPrice;
    private TextView txtSolOir;
    private TextView txtBtcPrice;
    private TextView txtBtcOir;
    private TextView txtConsoleLog;
    private ScrollView scrollConsole;
    private Button btnToggleHarvest;
    private Button btnExportDb;
    private Button btnClearDb;

    private MarketDataCollector collector;
    private final StringBuilder logBuilder = new StringBuilder();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Make Status Bar & Navigation Dark Cyberpunk
        Window window = getWindow();
        window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS);
        window.setStatusBarColor(Color.parseColor("#050814"));
        window.setNavigationBarColor(Color.parseColor("#050814"));

        setContentView(R.layout.activity_main);

        bindViews();
        setupListeners();

        collector = MarketDataCollector.getInstance(this);
        collector.setListener(this);

        updateInitialState();
    }

    private void bindViews() {
        txtStatusBadge = findViewById(R.id.txtStatusBadge);
        txtDataCount = findViewById(R.id.txtDataCount);
        txtTotalPnl = findViewById(R.id.txtTotalPnl);
        txtAlphaScore = findViewById(R.id.txtAlphaScore);
        txtSolPrice = findViewById(R.id.txtSolPrice);
        txtSolOir = findViewById(R.id.txtSolOir);
        txtBtcPrice = findViewById(R.id.txtBtcPrice);
        txtBtcOir = findViewById(R.id.txtBtcOir);
        txtConsoleLog = findViewById(R.id.txtConsoleLog);
        scrollConsole = findViewById(R.id.scrollConsole);
        btnToggleHarvest = findViewById(R.id.btnToggleHarvest);
        btnExportDb = findViewById(R.id.btnExportDb);
        btnClearDb = findViewById(R.id.btnClearDb);
    }

    private void setupListeners() {
        btnToggleHarvest.setOnClickListener(v -> toggleHarvest());
        btnExportDb.setOnClickListener(v -> exportDatabase());
        btnClearDb.setOnClickListener(v -> confirmClearDb());
    }

    private void updateInitialState() {
        int initialCount = collector.getDbHelper().getTelemetryCount();
        double initialPnl = collector.getDbHelper().getTotalPnl();

        txtDataCount.setText(String.format(Locale.US, "%,d Kayıt", initialCount));
        txtTotalPnl.setText(String.format(Locale.US, "%+$0.2f", initialPnl));

        if (collector.isRunning()) {
            setUiActiveState(true);
        } else {
            setUiActiveState(false);
        }
    }

    private void toggleHarvest() {
        if (collector.isRunning()) {
            stopHarvestService();
            setUiActiveState(false);
            Toast.makeText(this, "🛑 7/24 Veri Toplayıcı Durduruldu", Toast.LENGTH_SHORT).show();
        } else {
            startHarvestService();
            setUiActiveState(true);
            Toast.makeText(this, "🚀 7/24 Veri Toplama Başlatıldı!", Toast.LENGTH_SHORT).show();
        }
    }

    private void startHarvestService() {
        Intent serviceIntent = new Intent(this, HyperNovaService.class);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(serviceIntent);
        } else {
            startService(serviceIntent);
        }
    }

    private void stopHarvestService() {
        Intent serviceIntent = new Intent(this, HyperNovaService.class);
        stopService(serviceIntent);
        collector.stop();
    }

    private void setUiActiveState(boolean active) {
        if (active) {
            txtStatusBadge.setText("🟢 7/24 AKTİF (KAYITTA)");
            txtStatusBadge.setBackgroundResource(R.drawable.badge_active);
            txtStatusBadge.setTextColor(Color.parseColor("#00ff88"));

            btnToggleHarvest.setText("🔴 VERİ TOPLAMAYI DURDUR");
            btnToggleHarvest.setBackgroundResource(R.drawable.btn_stop);
            btnToggleHarvest.setTextColor(Color.WHITE);
        } else {
            txtStatusBadge.setText("🔴 DURDURULDU");
            txtStatusBadge.setBackgroundResource(R.drawable.badge_inactive);
            txtStatusBadge.setTextColor(Color.parseColor("#ff3366"));

            btnToggleHarvest.setText("🟢 7/24 VERİ TOPLAMAYI BAŞLAT");
            btnToggleHarvest.setBackgroundResource(R.drawable.btn_start);
            btnToggleHarvest.setTextColor(Color.parseColor("#050814"));
        }
    }

    @Override
    public void onMarketUpdate(MarketDataCollector.MarketSnapshot snap) {
        runOnUiThread(() -> {
            txtDataCount.setText(String.format(Locale.US, "%,d Kayıt", snap.totalRecords));
            txtTotalPnl.setText(String.format(Locale.US, "%+$0.2f", snap.totalPnl));

            if (snap.totalPnl >= 0) {
                txtTotalPnl.setTextColor(Color.parseColor("#00ff88"));
            } else {
                txtTotalPnl.setTextColor(Color.parseColor("#ff3366"));
            }

            if (snap.solPrice > 0) {
                txtSolPrice.setText(String.format(Locale.US, "$%.2f", snap.solPrice));
                txtSolOir.setText(String.format(Locale.US, "L2 OIR: %+.1f%% | Fund: %+.3f%%", snap.solOir, snap.solFunding));
            }

            if (snap.btcPrice > 0) {
                txtBtcPrice.setText(String.format(Locale.US, "$%,.1f", snap.btcPrice));
                txtBtcOir.setText(String.format(Locale.US, "L2 OIR: %+.1f%% | Fund: %+.3f%%", snap.btcOir, snap.btcFunding));
            }

            if (snap.alphaScore > 25) {
                txtAlphaScore.setText(String.format(Locale.US, "%+.1f (AL)", snap.alphaScore));
                txtAlphaScore.setTextColor(Color.parseColor("#00ff88"));
            } else if (snap.alphaScore < -25) {
                txtAlphaScore.setText(String.format(Locale.US, "%+.1f (SAT)", snap.alphaScore));
                txtAlphaScore.setTextColor(Color.parseColor("#ff3366"));
            } else {
                txtAlphaScore.setText(String.format(Locale.US, "%+.1f (NÖTR)", snap.alphaScore));
                txtAlphaScore.setTextColor(Color.parseColor("#8c9fc2"));
            }
        });
    }

    @Override
    public void onLog(String message) {
        runOnUiThread(() -> {
            if (logBuilder.length() > 5000) {
                logBuilder.delete(0, 2000);
            }
            logBuilder.append(message).append("\n");
            txtConsoleLog.setText(logBuilder.toString());
            scrollConsole.post(() -> scrollConsole.fullScroll(View.FOCUS_DOWN));
        });
    }

    private void exportDatabase() {
        try {
            File dbFile = TradeDatabaseHelper.getDatabaseFile(this);
            if (!dbFile.exists()) {
                Toast.makeText(this, "Henüz toplanmış veritabanı yok!", Toast.LENGTH_SHORT).show();
                return;
            }

            File exportDir = new File(getFilesDir(), "exports");
            if (!exportDir.exists()) exportDir.mkdirs();
            File exportFile = new File(exportDir, "trade_memory.db");

            try (FileChannel in = new FileInputStream(dbFile).getChannel();
                 FileChannel out = new FileOutputStream(exportFile).getChannel()) {
                out.transferFrom(in, 0, in.size());
            }

            Uri fileUri = FileProvider.getUriForFile(this, "com.hypernova.app.fileprovider", exportFile);

            Intent shareIntent = new Intent(Intent.ACTION_SEND);
            shareIntent.setType("application/octet-stream");
            shareIntent.putExtra(Intent.EXTRA_STREAM, fileUri);
            shareIntent.putExtra(Intent.EXTRA_SUBJECT, "HyperNova trade_memory.db Telemetri");
            shareIntent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);

            startActivity(Intent.createChooser(shareIntent, "Veritabanını Bilgisayara / Uygulamaya Paylaş"));

        } catch (Exception e) {
            Toast.makeText(this, "Dışa aktarma hatası: " + e.getMessage(), Toast.LENGTH_LONG).show();
        }
    }

    private void confirmClearDb() {
        new AlertDialog.Builder(this)
                .setTitle("Veritabanını Sıfırla")
                .setMessage("Toplanan tüm telemetri ve trade kayıtlarını silmek istediğinize emin misiniz?")
                .setPositiveButton("Evet, Temizle", (dialog, which) -> {
                    collector.getDbHelper().clearAllData();
                    updateInitialState();
                    Toast.makeText(this, "Veritabanı temizlendi.", Toast.LENGTH_SHORT).show();
                })
                .setNegativeButton("İptal", null)
                .show();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (collector != null) {
            collector.setListener(this);
            updateInitialState();
        }
    }

    @Override
    public void onBackPressed() {
        // Minimize to background without killing 7/24 harvest service
        moveTaskToBack(true);
    }
}

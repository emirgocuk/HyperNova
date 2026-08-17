"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import {
  Flame, Zap, Brain, Settings, Play, Pause, AlertOctagon,
  RefreshCw, TrendingUp, TrendingDown, DollarSign, Shield,
  Activity, Smartphone, Database, CheckCircle2, ChevronRight,
  BarChart2, Terminal as TerminalIcon, Award, Cpu, Radio
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

// ===================== TYPES =====================
type PortfolioStats = {
  balance: number;
  equity: number;
  unrealized_pnl: number;
  used_margin?: number;
  free_margin?: number;
  margin_level_pct?: number;
  open_positions: number;
};

type Microstructure = {
  bid_vol?: number;
  ask_vol?: number;
  oir?: number;
  oir_pct?: number;
  funding_apr?: number;
  oi_millions?: number;
  vol_millions?: number;
  basis_pct?: number;
  composite_alpha?: number;
};

type Position = {
  symbol: string;
  side: "LONG" | "SHORT";
  size_coin: number;
  notional_usd: number;
  required_margin: number;
  leverage: number;
  entry_price: number;
  current_price: number;
  price_change_pct: number;
  pnl_usd: number;
  roe_pct: number;
  sl_price?: number;
  tp_price?: number;
  duration_str: string;
  entry_time: string;
};

type SystemStatus = {
  status: string;
  is_bot_active: boolean;
  is_training: boolean;
  balance: number;
  equity: number;
  unrealized_pnl: number;
  realized_pnl: number;
  used_margin: number;
  free_margin: number;
  margin_level_pct: number;
  leverage: number;
  open_positions: number;
  prices: Record<string, number>;
  microstructure: Record<string, Microstructure>;
  device_id?: string;
  timestamp?: string;
};

type TrainingStatus = {
  total_nodes_connected: number;
  nodes_list: Array<{ device_id: string; trades_count: number; last_sync: string }>;
  total_crowdsourced_trades: number;
  local_node_stats: Record<string, any>;
  current_rules: Record<string, any> | null;
  data_lake_files_count: number;
  is_training: boolean;
};

type LogMessage = {
  id: number;
  timestamp: string;
  message: string;
  type: string;
};

type EngineConfig = {
  symbols: string[];
  leverage: number;
  max_positions: number;
  lot_size_usd_notional: number;
  base_profit_trigger: number;
  fast_sl_pct: number;
  stagnant_timeout_seconds: number;
  is_live_trading: boolean;
};

export default function HyperNovaApp() {
  const [activeTab, setActiveTab] = useState<"scalper" | "ai" | "settings">("scalper");
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [positions, setPositions] = useState<Position[]>([]);
  const [trainingStatus, setTrainingStatus] = useState<TrainingStatus | null>(null);
  const [logs, setLogs] = useState<LogMessage[]>([]);
  const [config, setConfig] = useState<EngineConfig | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [isActionLoading, setIsActionLoading] = useState(false);
  const [trainingMsg, setTrainingMsg] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const terminalEndRef = useRef<HTMLDivElement | null>(null);

  const API_BASE = typeof window !== "undefined" && window.location.hostname !== "localhost" 
    ? `http://${window.location.hostname}:8000` 
    : "http://localhost:8000";

  const WS_URL = typeof window !== "undefined" && window.location.hostname !== "localhost" 
    ? `ws://${window.location.hostname}:8000/ws/live` 
    : "ws://localhost:8000/ws/live";

  // Auto scroll terminal
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // Fetch initial REST data
  const refreshData = useCallback(async () => {
    try {
      const [sRes, pRes, tRes, cRes] = await Promise.all([
        fetch(`${API_BASE}/api/v1/status`),
        fetch(`${API_BASE}/api/v1/positions`),
        fetch(`${API_BASE}/api/v1/training/status`),
        fetch(`${API_BASE}/api/v1/config`)
      ]);

      if (sRes.ok) setStatus(await sRes.json());
      if (pRes.ok) setPositions(await pRes.json());
      if (tRes.ok) setTrainingStatus(await tRes.json());
      if (cRes.ok) setConfig(await cRes.json());
    } catch (err) {
      console.warn("REST API polling error:", err);
    }
  }, [API_BASE]);

  // Setup WebSocket connection
  useEffect(() => {
    refreshData();
    const interval = setInterval(refreshData, 3000);

    const connectWs = () => {
      try {
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          setWsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === "INIT" || data.type === "TICK") {
              if (data.prices || data.stats) {
                setStatus((prev) => prev ? {
                  ...prev,
                  prices: data.prices || prev.prices,
                  microstructure: data.microstructure || prev.microstructure,
                  balance: data.stats?.balance ?? prev.balance,
                  equity: data.stats?.equity ?? prev.equity,
                  unrealized_pnl: data.stats?.unrealized_pnl ?? prev.unrealized_pnl,
                  used_margin: data.stats?.used_margin ?? prev.used_margin,
                  is_bot_active: data.is_running ?? prev.is_bot_active,
                } : null);
              }
              if (data.logs) {
                setLogs((prev) => {
                  const combined = [...data.logs, ...prev];
                  const unique = Array.from(new Map(combined.map(item => [item.id, item])).values());
                  return unique.slice(0, 80);
                });
              }
            }
          } catch (e) {
            console.error("WS Parse Error", e);
          }
        };

        ws.onclose = () => {
          setWsConnected(false);
          setTimeout(connectWs, 3000);
        };

        ws.onerror = () => {
          setWsConnected(false);
          ws.close();
        };
      } catch (err) {
        setWsConnected(false);
      }
    };

    connectWs();

    return () => {
      clearInterval(interval);
      if (wsRef.current) wsRef.current.close();
    };
  }, [WS_URL, refreshData]);

  // Actions
  const handleToggleBot = async () => {
    setIsActionLoading(true);
    const endpoint = status?.is_bot_active ? "stop" : "start";
    try {
      await fetch(`${API_BASE}/api/v1/control/${endpoint}`, { method: "POST" });
      await refreshData();
    } finally {
      setIsActionLoading(false);
    }
  };

  const handlePanic = async () => {
    if (!confirm("⚠️ TÜM AÇIK POZİSYONLAR ANINDA PİYASA FİYATINDAN KAPATILSIN MI?")) return;
    setIsActionLoading(true);
    try {
      await fetch(`${API_BASE}/api/v1/control/panic`, { method: "POST" });
      await refreshData();
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleStartTraining = async () => {
    setTrainingMsg("Eğitim başlatılıyor...");
    try {
      const res = await fetch(`${API_BASE}/api/v1/training/start`, { method: "POST" });
      const data = await res.json();
      setTrainingMsg(data.message || "Eğitim arka planda çalışıyor.");
      setTimeout(() => {
        refreshData();
        setTrainingMsg(null);
      }, 4000);
    } catch (err) {
      setTrainingMsg("Eğitim başlatılamadı.");
    }
  };

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!config) return;
    setIsActionLoading(true);
    try {
      await fetch(`${API_BASE}/api/v1/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config)
      });
      alert("✅ Ayarlar başarıyla kaydedildi!");
      await refreshData();
    } finally {
      setIsActionLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans pb-12">
      {/* Top Navbar */}
      <header className="sticky top-0 z-50 bg-slate-900/80 backdrop-blur-md border-b border-slate-800/80 px-4 lg:px-8 py-3">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
          
          {/* Logo & Subtitle */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-amber-500 via-rose-600 to-indigo-600 flex items-center justify-center shadow-lg shadow-rose-500/20">
              <Flame className="w-6 h-6 text-white animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-black tracking-tight text-white">HyperNova</h1>
                <span className="text-[10px] uppercase font-extrabold px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-400 border border-rose-500/30">
                  1000:1 Engine
                </span>
              </div>
              <p className="text-xs text-slate-400 font-medium">Edge-Cloud AI & HFT Microstructure Scalper</p>
            </div>
          </div>

          {/* Quick Stats & Controls */}
          <div className="flex items-center gap-3 flex-wrap">
            {/* Live WebSocket Indicator */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800/60 border border-slate-700/60 text-xs">
              <Radio className={`w-3.5 h-3.5 ${wsConnected ? "text-emerald-400 animate-pulse" : "text-amber-400"}`} />
              <span className={wsConnected ? "text-emerald-400 font-semibold" : "text-amber-400 font-semibold"}>
                {wsConnected ? "WS Canlı" : "Yenileniyor"}
              </span>
            </div>

            {/* Start / Pause Button */}
            <button
              onClick={handleToggleBot}
              disabled={isActionLoading}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl font-bold text-xs shadow-md transition-all ${
                status?.is_bot_active
                  ? "bg-amber-500/20 text-amber-300 border border-amber-500/40 hover:bg-amber-500/30"
                  : "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 hover:bg-emerald-500/30"
              }`}
            >
              {status?.is_bot_active ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
              {status?.is_bot_active ? "Motoru Duraklat" : "Motoru Başlat"}
            </button>

            {/* Panic Stop Button */}
            <button
              onClick={handlePanic}
              disabled={isActionLoading}
              className="flex items-center gap-2 px-3 py-2 rounded-xl font-bold text-xs bg-rose-600/20 text-rose-300 border border-rose-500/40 hover:bg-rose-600/40 shadow-lg shadow-rose-900/30 transition-all"
              title="Tüm pozisyonları piyasa fiyatından anında kapat"
            >
              <AlertOctagon className="w-4 h-4 text-rose-400" />
              <span>Panik Kapat</span>
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="max-w-7xl mx-auto mt-3 flex border-b border-slate-800 gap-2">
          <button
            onClick={() => setActiveTab("scalper")}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-bold border-b-2 transition-all ${
              activeTab === "scalper"
                ? "border-rose-500 text-rose-400 bg-rose-500/10 rounded-t-lg"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Zap className="w-4 h-4" />
            <span>⚡ 1000:1 Canlı Scalper</span>
          </button>
          <button
            onClick={() => setActiveTab("ai")}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-bold border-b-2 transition-all ${
              activeTab === "ai"
                ? "border-indigo-500 text-indigo-400 bg-indigo-500/10 rounded-t-lg"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Brain className="w-4 h-4" />
            <span>🧠 AI Telemetri İstasyonu</span>
          </button>
          <button
            onClick={() => setActiveTab("settings")}
            className={`flex items-center gap-2 px-4 py-2.5 text-sm font-bold border-b-2 transition-all ${
              activeTab === "settings"
                ? "border-cyan-500 text-cyan-400 bg-cyan-500/10 rounded-t-lg"
                : "border-transparent text-slate-400 hover:text-slate-200"
            }`}
          >
            <Settings className="w-4 h-4" />
            <span>⚙️ Strateji & Risk</span>
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto w-full px-4 lg:px-8 mt-6 flex-1">
        
        {/* ========================================================= */}
        {/* TAB 1: 1000:1 LIVE SCALPER HUB */}
        {/* ========================================================= */}
        {activeTab === "scalper" && (
          <div className="space-y-6">
            
            {/* Portfolio Summary Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              
              {/* Balance */}
              <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-lg">
                <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                  <span>💰 Toplam Bakiye (Balance)</span>
                  <span className="text-[11px] font-bold text-rose-400 bg-rose-500/10 px-2 py-0.5 rounded border border-rose-500/20">
                    {status?.leverage || 1000}:1
                  </span>
                </div>
                <div className="text-2xl font-black text-white">
                  ${(status?.balance ?? 10000).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  Kullanılabilir Bakiye
                </div>
              </div>

              {/* Equity */}
              <div className="p-4 rounded-2xl bg-gradient-to-br from-indigo-950/40 via-slate-900/60 to-slate-900 border border-indigo-500/30 shadow-lg">
                <div className="flex items-center justify-between text-xs text-indigo-300 mb-1">
                  <span>📈 Toplam Varlık (Equity)</span>
                  <Activity className="w-3.5 h-3.5 text-indigo-400" />
                </div>
                <div className="text-2xl font-black text-indigo-200">
                  ${(status?.equity ?? 10000).toLocaleString("en-US", { minimumFractionDigits: 2 })}
                </div>
                <div className="text-xs font-semibold text-indigo-400 mt-1">
                  Kâr/Zarar Dahil Gerçekleşen
                </div>
              </div>

              {/* Unrealized PnL */}
              <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-lg">
                <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                  <span>💸 Açık Kâr/Zarar</span>
                  <span className="text-xs text-slate-400">{positions.length} Açık Poz</span>
                </div>
                <div className={`text-2xl font-black ${
                  (status?.unrealized_pnl ?? 0) >= 0 ? "text-emerald-400" : "text-rose-400"
                }`}>
                  {(status?.unrealized_pnl ?? 0) >= 0 ? "+" : ""}${(status?.unrealized_pnl ?? 0).toFixed(2)}
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  Gerçekleşmiş: ${(status?.realized_pnl ?? 0).toFixed(2)}
                </div>
              </div>

              {/* Margin Info */}
              <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 shadow-lg">
                <div className="flex items-center justify-between text-xs text-slate-400 mb-1">
                  <span>🛡️ Teminat (Margin)</span>
                  <Shield className="w-3.5 h-3.5 text-slate-400" />
                </div>
                <div className="text-xl font-bold text-white">
                  ${(status?.used_margin ?? 0).toFixed(2)} <span className="text-xs font-normal text-slate-500">kullanılan</span>
                </div>
                <div className="text-xs text-emerald-400 font-medium mt-1">
                  Serbest: ${(status?.free_margin ?? 10000).toFixed(2)}
                </div>
              </div>
            </div>

            {/* Real-Time Microstructure Gauges (SOL, HYPE, BTC) */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
                  <BarChart2 className="w-4 h-4 text-rose-400" />
                  <span>4-Faktörlü L2 Piyasa Mikroyapısı (Real-Time Orderbook)</span>
                </h2>
                <span className="text-xs text-slate-500">HyperLiquid L2 Derinlik Feed</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {(config?.symbols || ["SOL", "HYPE", "BTC"]).map((sym) => {
                  const px = status?.prices?.[sym] ?? 0;
                  const micro = status?.microstructure?.[sym] || {};
                  const oir = micro.oir_pct ?? 0;
                  const alpha = micro.composite_alpha ?? 0;
                  const funding = micro.funding_apr ?? 0;

                  return (
                    <div key={sym} className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/90 shadow-xl relative overflow-hidden">
                      {/* Alpha Score Gradient Header */}
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="text-lg font-black text-white">{sym}</span>
                          <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                            1m Scalp
                          </span>
                        </div>
                        <div className={`px-2.5 py-1 rounded-lg text-xs font-black flex items-center gap-1 ${
                          alpha > 15 
                            ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" 
                            : alpha < -15 
                            ? "bg-rose-500/20 text-rose-400 border border-rose-500/30" 
                            : "bg-slate-800 text-slate-400"
                        }`}>
                          <span>Alpha: {alpha > 0 ? `+${alpha}` : alpha}</span>
                        </div>
                      </div>

                      {/* Current Price */}
                      <div className="text-2xl font-black tracking-tight text-white mb-4">
                        ${px > 0 ? px.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 4 }) : "---"}
                      </div>

                      {/* L2 Orderbook Imbalance (OIR) Bar */}
                      <div className="space-y-1.5 mb-4">
                        <div className="flex justify-between text-xs font-medium">
                          <span className="text-slate-400">L2 Tahta Dengesi (OIR)</span>
                          <span className={oir >= 0 ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>
                            {oir > 0 ? `+${oir}% Alıcı` : `${oir}% Satıcı`}
                          </span>
                        </div>
                        <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden flex">
                          <div
                            className="bg-emerald-500 transition-all duration-300"
                            style={{ width: `${Math.max(0, Math.min(100, 50 + oir / 2))}%` }}
                          />
                          <div
                            className="bg-rose-500 transition-all duration-300"
                            style={{ width: `${Math.max(0, Math.min(100, 50 - oir / 2))}%` }}
                          />
                        </div>
                      </div>

                      {/* Metric Grid */}
                      <div className="grid grid-cols-2 gap-2 text-xs pt-2 border-t border-slate-800/80">
                        <div>
                          <span className="text-slate-500 block">Fonlama APR</span>
                          <span className="font-bold text-slate-300">{funding.toFixed(2)}%</span>
                        </div>
                        <div>
                          <span className="text-slate-500 block">Açık Poz (OI)</span>
                          <span className="font-bold text-slate-300">${micro.oi_millions ?? 0}M</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Open Positions Section */}
            <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/90 shadow-xl">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-base font-bold text-white flex items-center gap-2">
                  <Activity className="w-4 h-4 text-emerald-400" />
                  <span>Canlı Açık Pozisyonlar ({positions.length})</span>
                </h3>
                <span className="text-xs text-slate-500 font-mono">1000:1 Mikro-Teminat</span>
              </div>

              {positions.length === 0 ? (
                <div className="text-center py-10 text-slate-500 text-sm">
                  ⚡ Şu anda açık pozisyon yok. Scalper motoru 4-faktörlü teyitli sinyal arıyor...
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400">
                        <th className="pb-3">Varlık</th>
                        <th className="pb-3">Yön</th>
                        <th className="pb-3">Giriş / Anlık</th>
                        <th className="pb-3">Hacim / Teminat</th>
                        <th className="pb-3">Süre</th>
                        <th className="pb-3">Kâr/Zarar (USD)</th>
                        <th className="pb-3">ROE %</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {positions.map((p, idx) => (
                        <tr key={idx} className="hover:bg-slate-800/30">
                          <td className="py-3 font-bold text-white">{p.symbol}</td>
                          <td className="py-3">
                            <span className={`px-2 py-0.5 rounded font-extrabold text-[11px] ${
                              p.side === "LONG" 
                                ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" 
                                : "bg-rose-500/20 text-rose-400 border border-rose-500/30"
                            }`}>
                              {p.side}
                            </span>
                          </td>
                          <td className="py-3 font-mono">
                            ${p.entry_price.toFixed(4)} ➔ ${p.current_price.toFixed(4)}
                          </td>
                          <td className="py-3">
                            <span className="font-semibold text-slate-200">${p.notional_usd}</span>
                            <span className="text-slate-500 block">Teminat: ${p.required_margin}</span>
                          </td>
                          <td className="py-3 font-mono text-slate-400">{p.duration_str}</td>
                          <td className={`py-3 font-bold font-mono ${p.pnl_usd >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                            {p.pnl_usd >= 0 ? "+" : ""}${p.pnl_usd.toFixed(2)}
                          </td>
                          <td className={`py-3 font-black ${p.roe_pct >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                            {p.roe_pct >= 0 ? "+" : ""}{p.roe_pct.toFixed(1)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Live Terminal & Logs */}
            <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800/90 shadow-xl">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <TerminalIcon className="w-4 h-4 text-rose-400" />
                  <span className="text-sm font-bold text-white">Canlı Terminal Akışı</span>
                </div>
                <span className="text-[11px] text-slate-500 font-mono">WebSocket Stream</span>
              </div>
              <div className="h-44 bg-slate-950 rounded-xl p-3 font-mono text-xs overflow-y-auto space-y-1.5 border border-slate-900">
                {logs.length === 0 ? (
                  <div className="text-slate-600 italic">Sistem mesajları bekleniyor...</div>
                ) : (
                  logs.map((log) => (
                    <div key={log.id} className="flex items-start gap-2">
                      <span className="text-slate-600 font-mono">[{log.timestamp}]</span>
                      <span className={`font-semibold ${
                        log.type === "PROFIT" ? "text-emerald-400" :
                        log.type === "LOSS" ? "text-rose-400" :
                        log.type === "ORDER" ? "text-amber-300" :
                        log.type === "PANIC" ? "text-rose-500 font-bold" :
                        "text-slate-300"
                      }`}>
                        {log.message}
                      </span>
                    </div>
                  ))
                )}
                <div ref={terminalEndRef} />
              </div>
            </div>

          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 2: AI TELEMETRY & FEDERATED TRAINING HUB */}
        {/* ========================================================= */}
        {activeTab === "ai" && (
          <div className="space-y-6">
            
            {/* Top Training Card Banner */}
            <div className="p-6 rounded-3xl bg-gradient-to-r from-indigo-950 via-slate-900 to-slate-900 border border-indigo-500/40 shadow-2xl relative overflow-hidden">
              <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Brain className="w-6 h-6 text-indigo-400" />
                    <h2 className="text-xl font-black text-white">Merkezi Yapay Zeka Eğitim İstasyonu</h2>
                  </div>
                  <p className="text-sm text-slate-300 max-w-2xl">
                    Arkadaşlarınızın telefonlarından ve yerel botunuzdan toplanan tüm L2 işlem tecrübelerini birleştirir (Federe Veri Madenciliği), zararlı sinyalleri filtreler ve optimal strateji kurallarını üretir.
                  </p>
                </div>
                
                <button
                  onClick={handleStartTraining}
                  disabled={trainingStatus?.is_training}
                  className="px-6 py-3 rounded-2xl bg-gradient-to-r from-indigo-600 to-rose-600 hover:from-indigo-500 hover:to-rose-500 text-white font-black text-sm shadow-xl shadow-indigo-600/30 flex items-center gap-2 transition-all transform active:scale-95"
                >
                  <Cpu className="w-5 h-5" />
                  <span>{trainingStatus?.is_training ? "Eğitiliyor..." : "Federe Modeli Eğit"}</span>
                </button>
              </div>

              {trainingMsg && (
                <div className="mt-4 p-3 rounded-xl bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 text-xs font-semibold">
                  {trainingMsg}
                </div>
              )}
            </div>

            {/* AI Data Stats */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800">
                <div className="flex items-center gap-2 text-xs text-slate-400 mb-1">
                  <Smartphone className="w-4 h-4 text-indigo-400" />
                  <span>Bağlı Mobil Cihazlar</span>
                </div>
                <div className="text-3xl font-black text-white">
                  {trainingStatus?.total_nodes_connected ?? 1}
                </div>
                <div className="text-xs text-slate-500 mt-1">Federe Veri Düğümleri</div>
              </div>

              <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800">
                <div className="flex items-center gap-2 text-xs text-slate-400 mb-1">
                  <Database className="w-4 h-4 text-rose-400" />
                  <span>Toplanan İşlem Tecrübesi</span>
                </div>
                <div className="text-3xl font-black text-rose-300">
                  {(trainingStatus?.total_crowdsourced_trades ?? 0).toLocaleString()}
                </div>
                <div className="text-xs text-slate-500 mt-1">Kayıtlı Al-Sat & Telemetri</div>
              </div>

              <div className="p-5 rounded-2xl bg-slate-900/70 border border-slate-800">
                <div className="flex items-center gap-2 text-xs text-slate-400 mb-1">
                  <Award className="w-4 h-4 text-amber-400" />
                  <span>Veri Ambarı Dosyaları</span>
                </div>
                <div className="text-3xl font-black text-amber-300">
                  {trainingStatus?.data_lake_files_count ?? 0}
                </div>
                <div className="text-xs text-slate-500 mt-1">Senkronize JSON Paketleri</div>
              </div>
            </div>

            {/* Learned Optimal Rules Display */}
            <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800">
              <h3 className="text-base font-bold text-white mb-3 flex items-center gap-2">
                <Award className="w-4 h-4 text-indigo-400" />
                <span>Öğrenilmiş Optimal Strateji Kuralları (Edge Rules)</span>
              </h3>

              {trainingStatus?.current_rules ? (
                <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 font-mono text-xs text-indigo-300 overflow-x-auto">
                  <pre>{JSON.stringify(trainingStatus.current_rules, null, 2)}</pre>
                </div>
              ) : (
                <div className="text-sm text-slate-500 italic py-4">
                  Henüz eğitilmiş kural bulunamadı. "Federe Modeli Eğit" butonuna basarak ilk modeli üretebilirsiniz.
                </div>
              )}
            </div>

          </div>
        )}

        {/* ========================================================= */}
        {/* TAB 3: STRATEGY CONFIGURATION & RISK */}
        {/* ========================================================= */}
        {activeTab === "settings" && config && (
          <form onSubmit={handleSaveConfig} className="space-y-6 max-w-3xl">
            <div className="p-6 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-6">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Settings className="w-4 h-4 text-cyan-400" />
                <span>1000:1 Motor ve Risk Parametreleri</span>
              </h3>

              {/* Leverage */}
              <div>
                <label className="text-xs font-bold text-slate-300 block mb-1">
                  Kaldıraç Oranı ({config.leverage}:1)
                </label>
                <input
                  type="range"
                  min="50"
                  max="1000"
                  step="50"
                  value={config.leverage}
                  onChange={(e) => setConfig({ ...config, leverage: parseFloat(e.target.value) })}
                  className="w-full accent-rose-500 cursor-pointer"
                />
                <div className="flex justify-between text-[11px] text-slate-500 mt-1">
                  <span>50x</span>
                  <span>500x</span>
                  <span>1000:1 (Önerilen)</span>
                </div>
              </div>

              {/* Lot Size Notional */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold text-slate-300 block mb-1">
                    İşlem Başına Hacim (USD Notional)
                  </label>
                  <input
                    type="number"
                    value={config.lot_size_usd_notional}
                    onChange={(e) => setConfig({ ...config, lot_size_usd_notional: parseFloat(e.target.value) })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white font-mono"
                  />
                  <span className="text-[11px] text-slate-500">1000:1 kaldıraçta sadece ${(config.lot_size_usd_notional / config.leverage).toFixed(2)} teminat gerekir.</span>
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-300 block mb-1">
                    Maksimum Açık Pozisyon Sayısı
                  </label>
                  <input
                    type="number"
                    value={config.max_positions}
                    onChange={(e) => setConfig({ ...config, max_positions: parseInt(e.target.value) })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white font-mono"
                  />
                </div>
              </div>

              {/* SL and Timeout */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs font-bold text-slate-300 block mb-1">
                    Sıkı Stop-Loss (% Fiyat Hareketi)
                  </label>
                  <input
                    type="number"
                    step="0.0005"
                    value={config.fast_sl_pct}
                    onChange={(e) => setConfig({ ...config, fast_sl_pct: parseFloat(e.target.value) })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white font-mono"
                  />
                  <span className="text-[11px] text-slate-500">Örn: 0.0025 = %0.25 SL</span>
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-300 block mb-1">
                    Yatay Pozisyon Zaman Aşımı (Saniye)
                  </label>
                  <input
                    type="number"
                    value={config.stagnant_timeout_seconds}
                    onChange={(e) => setConfig({ ...config, stagnant_timeout_seconds: parseInt(e.target.value) })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-white font-mono"
                  />
                </div>
              </div>

              {/* Save Button */}
              <button
                type="submit"
                disabled={isActionLoading}
                className="w-full py-3 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-sm shadow-lg shadow-cyan-600/30 transition-all"
              >
                Ayarları Kaydet ve Uygula
              </button>
            </div>
          </form>
        )}

      </main>
    </div>
  );
}

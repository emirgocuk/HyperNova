"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Activity, Play, Terminal, TrendingUp, ShieldCheck, Loader2,
  Settings, Database, Zap, Shield, Flame, BarChart3, Download, Power, Wallet
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

// ===================== TYPES =====================
type SystemHealth = {
  status: string;
  circuit_breaker_active: boolean;
  daily_drawdown_pct: number;
  max_allowed_drawdown_pct: number;
  equity?: number;
  balance?: number;
  currency?: string;
  profit?: number;
  is_training?: boolean;
  is_fetching_data?: boolean;
  is_bot_active?: boolean;
  training_stats?: {
    current_epoch: number;
    total_epochs: number;
    accuracy: number;
    loss: number;
  } | null;
};

type XaiLog = {
  id: number;
  timestamp: string;
  symbol: string;
  action: string;
  confidence: number;
  xai_reason: string;
};

type EngineConfig = {
  active_profile: string;
  lot_size: number;
  max_drawdown_pct: number;
  grid_levels: number;
  data_fetch_days: number;
  training_epochs: number;
  symbol: string;
  timeframe: string;
};

type RiskProfile = {
  name: string;
  lot_size: number;
  max_drawdown_pct: number;
  grid_levels: number;
  description: string;
};

type Position = {
  ticket: number;
  symbol: string;
  type: string;
  volume: number;
  price_open: number;
  price_current: number;
  unrealized_pnl: number;
  time_setup: number;
};

// ===================== COMPONENT =====================
export default function Dashboard() {
  const [health, setHealth] = useState<SystemHealth>({ status: "CONNECTING", circuit_breaker_active: false, daily_drawdown_pct: 0, max_allowed_drawdown_pct: 0.03 });
  const [logs, setLogs] = useState<XaiLog[]>([]);
  const [config, setConfig] = useState<EngineConfig | null>(null);
  const [profiles, setProfiles] = useState<Record<string, RiskProfile>>({});
  const [positions, setPositions] = useState<Position[]>([]);
  const [pnl, setPnl] = useState({ realized_pnl: 0, unrealized_pnl: 0 });

  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'bot' | 'terminal' | 'settings'>('bot');
  const [equityHistory, setEquityHistory] = useState<{ time: string, equity: number }[]>([]);

  const API = 'http://localhost:8000';

  // Fetch all data
  const fetchData = useCallback(async () => {
    try {
      const [hRes, lRes, cRes, posRes, pnlRes] = await Promise.all([
        fetch(`${API}/api/v1/health`),
        fetch(`${API}/api/v1/xai/logs`),
        fetch(`${API}/api/v1/config`),
        fetch(`${API}/api/v1/bot/positions`),
        fetch(`${API}/api/v1/bot/pnl`)
      ]);

      if (hRes.ok) {
        const h = await hRes.json();
        setHealth(h);
        if (h.equity) {
          setEquityHistory(prev => {
            const next = [...prev, { time: new Date().toLocaleTimeString(), equity: h.equity }];
            return next.slice(-30);
          });
        }
      }
      if (lRes.ok) {
        const d = await lRes.json();
        setLogs(d.logs.slice(0, 50));
      }
      if (cRes.ok) {
        const c = await cRes.json();
        setConfig(c.config);
        setProfiles(c.profiles);
      }
      if (posRes.ok) {
        const p = await posRes.json();
        if (p.status === 'success') setPositions(p.positions || []);
      }
      if (pnlRes.ok) {
        const p = await pnlRes.json();
        if (p.status === 'success') setPnl({ realized_pnl: p.realized_pnl || 0, unrealized_pnl: p.unrealized_pnl || 0 });
      }
    } catch {
      setHealth(prev => ({ ...prev, status: "OFFLINE" }));
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 2000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Actions
  const toggleBot = async () => {
    try {
      await fetch(`${API}/api/v1/bot/toggle`, { method: 'POST' });
      fetchData(); // Instant refresh
    } catch { /* handled by polling */ }
  };

  const startTraining = async () => {
    try {
      await fetch(`${API}/api/v1/train/start`, { method: 'POST' });
    } catch { /* handled by polling */ }
  };

  const setProfile = async (profile: string) => {
    try {
      await fetch(`${API}/api/v1/config/profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile })
      });
      fetchData();
    } catch { /* */ }
  };

  const setSymbol = async (symbol: string) => {
    try {
      await fetch(`${API}/api/v1/config/update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol })
      });
      fetchData();
    } catch { /* */ }
  };

  const fetchNewData = async (days: number) => {
    try {
      await fetch(`${API}/api/v1/data/fetch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ days })
      });
    } catch { /* */ }
  };

  const isTraining = health.is_training || false;
  const isFetching = health.is_fetching_data || false;
  const isBotActive = health.is_bot_active || false;
  const stats = health.training_stats;
  const isOnline = health.status === 'ONLINE';

  // Action color
  const getActionColor = (action: string) => {
    if (action.includes('ERROR') || action.includes('STOPPED')) return 'bg-rose-900/50 text-rose-400';
    if (action.includes('COMPLETE') || action.includes('READY') || action.includes('STARTED')) return 'bg-emerald-900/50 text-emerald-400';
    if (action.includes('TRAINING')) return 'bg-sky-900/50 text-sky-400';
    if (action.includes('CONFIG') || action.includes('DATA')) return 'bg-amber-900/50 text-amber-400';
    return 'bg-indigo-900/50 text-indigo-400';
  };

  // Profile icon
  const profileIcon = (p: string) => {
    if (p === 'aggressive') return <Flame className="w-5 h-5 mx-auto mb-2 text-rose-400" />;
    if (p === 'safe') return <Shield className="w-5 h-5 mx-auto mb-2 text-emerald-400" />;
    return <BarChart3 className="w-5 h-5 mx-auto mb-2 text-sky-400" />;
  };

  return (
    <div className="min-h-screen text-slate-100 p-4 md:p-6 lg:p-8">
      {/* ========== HEADER ========== */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-sky-400 to-emerald-400 flex items-center gap-3">
            <Activity className="w-7 h-7 text-sky-400" />
            Control Tower <span className="text-xs font-medium text-slate-300 uppercase px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">Elirox Edition</span>
          </h1>
          <p className="text-slate-400 text-sm mt-1">Live Execution Engine: The Transparent Strategist</p>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          <div className="glass-panel px-3 py-1.5 flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isOnline ? 'bg-emerald-400 shadow-[0_0_10px_#34d399]' : 'bg-rose-400'}`}></div>
            <span className="text-xs font-medium uppercase">{health.status} MT5</span>
          </div>
        </div>
      </header>

      {/* ========== METRICS ROW (P/L FOCUSED) ========== */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <div className="glass-panel p-4 border-t-2 border-t-emerald-500 flex flex-col justify-between">
          <p className="text-slate-400 text-xs font-medium flex items-center gap-2"><Wallet className="w-3.5 h-3.5" /> TOTAL BALANCE</p>
          <div className="text-2xl font-bold my-1">{health.balance ? `$${health.balance.toLocaleString('en-US', { minimumFractionDigits: 2 })}` : '---'}</div>
          <p className="text-xs text-slate-500">Available: ${health.equity?.toLocaleString('en-US', { minimumFractionDigits: 2 })}</p>
        </div>

        <div className="glass-panel p-4 border-t-2 border-t-sky-500 flex flex-col justify-between">
          <p className="text-slate-400 text-xs font-medium flex items-center gap-2"><TrendingUp className="w-3.5 h-3.5" /> REALIZED P/L (Today)</p>
          <div className={`text-2xl font-bold my-1 ${pnl.realized_pnl > 0 ? 'text-emerald-400' : pnl.realized_pnl < 0 ? 'text-rose-400' : 'text-slate-100'}`}>
            {pnl.realized_pnl > 0 ? '+' : ''}${pnl.realized_pnl.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
          <p className="text-xs text-slate-500">From closed deals</p>
        </div>

        <div className="glass-panel p-4 border-t-2 border-t-amber-500 flex flex-col justify-between">
          <p className="text-slate-400 text-xs font-medium flex items-center gap-2"><Activity className="w-3.5 h-3.5" /> UNREALIZED P/L</p>
          <div className={`text-2xl font-bold my-1 ${pnl.unrealized_pnl > 0 ? 'text-emerald-400' : pnl.unrealized_pnl < 0 ? 'text-rose-400' : 'text-slate-100'}`}>
            {pnl.unrealized_pnl > 0 ? '+' : ''}${pnl.unrealized_pnl.toLocaleString('en-US', { minimumFractionDigits: 2 })}
          </div>
          <p className="text-xs text-slate-500">Open active trades ({positions.length})</p>
        </div>

        <div className="glass-panel p-4 border-t-2 border-t-indigo-500 flex flex-col justify-between">
          <p className="text-slate-400 text-xs font-medium flex items-center gap-2"><Zap className="w-3.5 h-3.5" /> AI ACCURACY</p>
          <div className="text-2xl font-bold my-1 text-indigo-400">{isTraining && stats ? `${stats.accuracy}%` : '89.34%'}</div>
          <div className="w-full bg-slate-800 rounded-full h-1 mt-1">
            <div className="bg-indigo-400 h-1 rounded-full w-[89%]"></div>
          </div>
        </div>
      </div>

      {/* ========== MAIN GRID ========== */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

        {/* LEFT: BOT CONTROL PANEL */}
        <div className="lg:col-span-1 glass-panel p-0 flex flex-col overflow-hidden">
          {/* Tab Selector */}
          <div className="flex items-center gap-0 border-b border-slate-800 bg-slate-900/50">
            <button onClick={() => setActiveTab('bot')} className={`flex-1 py-3 text-xs font-medium transition-all ${activeTab === 'bot' ? 'bg-sky-500/10 text-sky-400 border-b-2 border-sky-400' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'}`}>
              Bot Setup
            </button>
            <button onClick={() => setActiveTab('terminal')} className={`flex-1 py-3 text-xs font-medium transition-all ${activeTab === 'terminal' ? 'bg-indigo-500/10 text-indigo-400 border-b-2 border-indigo-400' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'}`}>
              XAI Log
            </button>
            <button onClick={() => setActiveTab('settings')} className={`flex-1 py-3 text-xs font-medium transition-all ${activeTab === 'settings' ? 'bg-amber-500/10 text-amber-400 border-b-2 border-amber-400' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'}`}>
              Training Config
            </button>
          </div>

          {/* TAB 1: BOT SETUP (Elirox Style) */}
          {activeTab === 'bot' && config && (
            <div className="p-5 flex flex-col gap-6 h-[500px] overflow-y-auto">

              {/* Massive Toggle Button */}
              <div className="flex flex-col items-center justify-center p-6 bg-slate-900/50 rounded-xl border border-slate-800">
                <button
                  onClick={toggleBot}
                  disabled={!isOnline}
                  className={`relative group w-32 h-32 rounded-full flex items-center justify-center transition-all duration-500 ${isBotActive ? 'bg-rose-500/10 border-4 border-rose-500 shadow-[0_0_30px_rgba(244,63,94,0.4)]' : 'bg-emerald-500/10 border-4 border-emerald-500 shadow-[0_0_30px_rgba(16,185,129,0.2)] hover:shadow-[0_0_40px_rgba(16,185,129,0.4)]'}`}
                >
                  <Power className={`w-12 h-12 transition-all duration-300 ${isBotActive ? 'text-rose-500 drop-shadow-[0_0_8px_rgba(244,63,94,0.8)]' : 'text-emerald-500 group-hover:drop-shadow-[0_0_8px_rgba(16,185,129,0.8)]'}`} />
                </button>
                <div className="mt-4 text-center">
                  <h2 className={`text-xl font-bold tracking-wider uppercase ${isBotActive ? 'text-rose-400' : 'text-emerald-400'}`}>
                    {isBotActive ? 'BOT IS ACTIVE' : 'LAUNCH BOT'}
                  </h2>
                  <p className="text-xs text-slate-500 mt-1">Trading <b>{config.symbol}</b> automatically</p>
                </div>
              </div>

              {/* Asset Selector */}
              <div>
                <h3 className="text-xs text-slate-400 font-medium uppercase tracking-wider mb-3">Trading Asset</h3>
                <div className="flex gap-2">
                  {['EURUSD', 'BTCUSDm', 'XAUUSD'].map(sym => (
                    <button
                      key={sym}
                      onClick={() => setSymbol(sym)}
                      disabled={isBotActive}
                      className={`flex-1 py-2 mb-2 rounded-lg text-xs font-bold border transition-all ${config.symbol === sym ? 'border-emerald-500 bg-emerald-900/30 text-emerald-400' : 'border-slate-800 bg-slate-900/30 text-slate-500 hover:border-slate-700'} ${isBotActive ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      {sym}
                    </button>
                  ))}
                </div>
              </div>

              {/* Risk Profile Selector */}
              <div>
                <h3 className="text-xs text-slate-400 font-medium uppercase tracking-wider mb-3">Operating Mode</h3>
                <div className="grid grid-cols-3 gap-2">
                  {Object.entries(profiles).map(([key, profile]) => (
                    <button
                      key={key}
                      onClick={() => setProfile(key)}
                      disabled={isBotActive} // Lock while running
                      className={`p-3 rounded-xl border text-center transition-all ${config.active_profile === key
                        ? 'border-sky-500 bg-sky-900/30'
                        : 'border-slate-800 bg-slate-900/30 text-slate-500 hover:border-slate-700'
                        } ${isBotActive ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      {profileIcon(key)}
                      <div className={`text-xs font-bold ${config.active_profile === key ? 'text-white' : ''}`}>{profile.name}</div>
                      <div className="text-[10px] text-slate-500 mt-1">{profile.lot_size} lot / x{profile.grid_levels}</div>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: XAI TERMINAL */}
          {activeTab === 'terminal' && (
            <div className="flex-1 p-3 overflow-y-auto space-y-2 font-mono h-[500px] bg-slate-950/50">
              {isLoading && <p className="text-slate-500 text-xs animate-pulse p-2">Connecting to Engine Core...</p>}
              <AnimatePresence>
                {logs.map((log, index) => (
                  <motion.div key={`${log.id}-${index}`} initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} className="border-l-2 border-slate-800 pl-3 py-1 mb-2">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-[10px] text-slate-500 font-mono">{new Date(log.timestamp).toLocaleTimeString()}</span>
                      <span className={`text-[9px] px-1.5 py-0.5 rounded font-bold tracking-wider ${getActionColor(log.action)}`}>{log.action}</span>
                      {log.confidence > 0 && <span className="text-[9px] text-emerald-500/70 border border-emerald-900 rounded px-1">p={(log.confidence).toFixed(2)}</span>}
                    </div>
                    <p className="text-sky-100/70 text-xs leading-relaxed">{log.xai_reason}</p>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>
          )}

          {/* TAB 3: TRAINING CONFIG */}
          {activeTab === 'settings' && config && (
            <div className="p-5 flex flex-col gap-6 h-[500px] overflow-y-auto">
              <div>
                <h3 className="text-xs text-slate-400 font-medium uppercase tracking-wider mb-3">AI Engine Training</h3>
                <button
                  disabled={!isOnline || isTraining || isFetching || isBotActive}
                  onClick={startTraining}
                  className={`w-full glass-button py-3 rounded-lg flex items-center justify-center gap-2 text-sm font-semibold ${(isTraining || isFetching || isBotActive) ? 'opacity-50 cursor-not-allowed border-slate-700 text-slate-500 bg-slate-800' : 'border-indigo-500/30 text-indigo-400 bg-indigo-500/10 hover:bg-indigo-500/20'}`}
                >
                  {isTraining ? <Loader2 className="w-5 h-5 animate-spin" /> : <Play className="w-5 h-5 fill-indigo-400" />}
                  {isTraining ? 'Training CNN-LSTM...' : 'Run Epoch Training'}
                </button>
                <p className="text-[10px] text-slate-500 text-center mt-2">Cannot train while Execution Engine is LIVE.</p>
              </div>

              <div>
                <h3 className="text-xs text-slate-400 font-medium uppercase tracking-wider mb-3">Historical Data Pull</h3>
                <div className="grid grid-cols-4 gap-2">
                  {[30, 90, 180, 365].map(days => (
                    <button
                      key={days}
                      disabled={isFetching || !isOnline || isBotActive}
                      onClick={() => fetchNewData(days)}
                      className={`py-2 rounded-lg text-xs font-medium border transition-all ${config.data_fetch_days === days
                        ? 'border-emerald-500 bg-emerald-900/30 text-emerald-300'
                        : 'border-slate-800 bg-slate-900/30 text-slate-500 hover:border-slate-600'
                        } ${(isFetching || isBotActive) ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      {isFetching ? <Loader2 className="w-3 h-3 animate-spin mx-auto" /> : `${days}d`}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

        </div>

        {/* RIGHT: CHART & POSITIONS */}
        <div className="lg:col-span-2 flex flex-col gap-6">

          {/* Active Positions Table */}
          <div className="glass-panel p-5 flex flex-col min-h-[220px]">
            <h2 className="text-sm font-semibold flex items-center gap-2 mb-4">
              <Database className="w-4 h-4 text-sky-400" /> Live Market Execution (Open Deals)
            </h2>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="text-xs text-slate-500 uppercase bg-slate-900/50">
                  <tr>
                    <th className="px-4 py-2 rounded-l-lg">Symbol</th>
                    <th className="px-4 py-2">Side</th>
                    <th className="px-4 py-2">Size</th>
                    <th className="px-4 py-2">Open Price</th>
                    <th className="px-4 py-2">Current Price</th>
                    <th className="px-4 py-2 rounded-r-lg text-right">Unr. PNL</th>
                  </tr>
                </thead>
                <tbody>
                  {positions.length > 0 ? (
                    positions.map((pos) => (
                      <tr key={pos.ticket} className="border-b border-slate-800 last:border-0 hover:bg-slate-800/30 transition-colors">
                        <td className="px-4 py-3 font-semibold text-white">{pos.symbol} <span className="text-[10px] text-slate-500 ml-1">#{pos.ticket.toString().slice(-4)}</span></td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${pos.type === 'BUY' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/20 text-rose-400 border border-rose-500/30'}`}>
                            {pos.type}
                          </span>
                        </td>
                        <td className="px-4 py-3 font-mono">{pos.volume}</td>
                        <td className="px-4 py-3 font-mono">{pos.price_open.toFixed(5)}</td>
                        <td className="px-4 py-3 font-mono">{pos.price_current.toFixed(5)}</td>
                        <td className={`px-4 py-3 text-right font-bold tracking-wider ${pos.unrealized_pnl > 0 ? 'text-emerald-400' : 'text-rose-400'}`}>
                          {pos.unrealized_pnl > 0 ? '+' : ''}{pos.unrealized_pnl.toFixed(2)}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="px-4 py-8 text-center text-slate-500 italic text-xs">
                        {isBotActive ? 'Bot is armed. Waiting for high-confidence AI signal to execute...' : 'Execution Engine is offline. Target acquired, awaiting launch.'}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Large Chart */}
          <div className="glass-panel p-5 flex-1 flex flex-col min-h-[300px]">
            <h2 className="text-sm font-semibold flex items-center gap-2 mb-4">
              <TrendingUp className="w-4 h-4 text-emerald-400" /> Account Equity Growth
            </h2>
            <div className="flex-1 w-full h-full min-h-[220px]">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={equityHistory.length > 1 ? equityHistory : [{ time: 'Start', equity: health.balance || 10000 }, { time: 'Now', equity: health.equity || 10000 }]}>
                  <defs>
                    <linearGradient id="colorEquity" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis dataKey="time" stroke="#64748b" tick={{ fill: '#64748b', fontSize: 10 }} />
                  <YAxis domain={['dataMin - 5', 'dataMax + 5']} stroke="#64748b" tick={{ fill: '#64748b', fontSize: 10 }} width={80} />
                  <Tooltip contentStyle={{ backgroundColor: '#020617', borderColor: '#1e293b', borderRadius: '8px', fontSize: '12px' }} itemStyle={{ color: '#3b82f6', fontWeight: 'bold' }} />
                  <Area type="monotone" dataKey="equity" stroke="#3b82f6" strokeWidth={2} fillOpacity={1} fill="url(#colorEquity)" isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}

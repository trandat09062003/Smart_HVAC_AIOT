import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import { 
  Thermometer, 
  Droplets, 
  Wind, 
  Activity, 
  Maximize2, 
  Bell, 
  User, 
  History,
  AlertTriangle,
  CloudRain,
  CloudSun,
  MapPin,
  RotateCw
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import mainLogo from '../img/main_logo_2.png';
import { MetricCard } from './components/MetricCard';
import { RealTimeChart } from './components/RealTimeChart';
import { ControlPanel } from './components/ControlPanel';
import { SensorReading, ChartDataPoint, HVACState, Status, TelemetryResponse, RemoteControlPayload, RemoteControlResponse, RemoteControlState, ZoneManagerInfo } from './types';
import { cn } from './lib/utils';

// Helper to determine status based on thresholds
const getStatus = (id: string, value: number): Status => {
  if (id === 'temp') {
    if (value > 26 || value < 18) return 'warning';
    return 'good';
  }
  if (id === 'humidity') {
    if (value > 60 || value < 30) return 'warning';
    return 'good';
  }
  if (id === 'co2') {
    if (value > 1000) return 'critical';
    if (value > 800) return 'warning';
    return 'good';
  }
  if (id === 'pm25') {
    if (value > 35) return 'critical';
    if (value > 12) return 'warning';
    return 'good';
  }
  return 'good';
};

interface HanoiWeather {
  temperature: number;
  apparentTemperature: number;
  humidity: number;
  windSpeed: number;
  minTemp: number;
  maxTemp: number;
  precipitationProbability: number;
  weatherCode: number;
}

type ControlField = keyof HVACState;

interface PendingControl {
  commandId: number;
  previousState: HVACState;
  desiredState: HVACState;
  fields: ControlField[];
}

interface ToastMessage {
  id: number;
  type: 'error' | 'info';
  message: string;
}

const CONTROL_FIELDS: ControlField[] = ['power', 'mode', 'targetTemp', 'fanSpeed'];

const getOrCreateClientId = () => {
  const key = 'smart-hvac-client-id';
  const existing = window.localStorage.getItem(key);
  if (existing) return existing;

  const next = window.crypto?.randomUUID?.() ?? `client-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  window.localStorage.setItem(key, next);
  return next;
};

const remoteToHVACState = (controlState: RemoteControlState): HVACState => ({
  power: controlState.power,
  mode: controlState.operationMode as any,
  targetTemp: controlState.temp,
  fanSpeed: controlState.fanPower as any,
  co2Max: controlState.co2Max ?? 800,
  humidityMax: controlState.humidityMax ?? 60,
});

const getControlRevision = (controlState: RemoteControlState) =>
  controlState.lastModifiedAt || controlState.time;

const formatClientLabel = (id: string) => `Người dùng ${id === 'unknown' ? 'khác' : id.slice(-6)}`;

const getWeatherLabel = (code: number) => {
  if (code === 0) return 'Clear';
  if ([1, 2, 3].includes(code)) return 'Partly Cloudy';
  if ([45, 48].includes(code)) return 'Foggy';
  if ([51, 53, 55, 56, 57].includes(code)) return 'Drizzle';
  if ([61, 63, 65, 66, 67, 80, 81, 82].includes(code)) return 'Rain';
  if ([95, 96, 99].includes(code)) return 'Thunderstorm';
  return 'Cloudy';
};

export default function App() {
  // --- STATE ---
  const [readings, setReadings] = useState<SensorReading[]>([
    { id: 'temp', name: 'Ambient Temp', value: 22.4, unit: '°C', status: 'good', trend: 1.2, icon: 'Thermometer' },
    { id: 'humidity', name: 'Relative Humidity', value: 45.1, unit: '%', status: 'good', trend: -0.5, icon: 'Droplets' },
    { id: 'co2', name: 'CO2 Levels', value: 420.0, unit: 'ppm', status: 'good', trend: 2.1, icon: 'Wind' },
    { id: 'pm25', name: 'Particulates (PM2.5)', value: 8.5, unit: 'µg/m³', status: 'good', trend: 0.8, icon: 'Activity' },
  ]);

  const [history, setHistory] = useState<ChartDataPoint[]>([]);
  const [latestValveAngle, setLatestValveAngle] = useState<number>(0);
  const [hvacState, setHvacState] = useState<HVACState>({
    power: true,
    mode: 'auto',
    targetTemp: 25.0,
    fanSpeed: 'auto',
    co2Max: 800,
    humidityMax: 60,
  });
  const [pendingControl, setPendingControl] = useState<PendingControl | null>(null);
  const [toast, setToast] = useState<ToastMessage | null>(null);
  const [hanoiWeather, setHanoiWeather] = useState<HanoiWeather | null>(null);
  const [isControlStateReady, setIsControlStateReady] = useState(false);
  const clientId = useMemo(getOrCreateClientId, []);
  const commandSequenceRef = useRef(0);
  const hvacStateRef = useRef(hvacState);
  const pendingControlRef = useRef<PendingControl | null>(null);
  const controlReadyRef = useRef(false);
  const lastControlRevisionRef = useRef<string | null>(null);
  const [zoneManager, setZoneManager] = useState<ZoneManagerInfo | null>(null);
  const [latestPower, setLatestPower] = useState<number>(0);
  const [latestEnergy, setLatestEnergy] = useState<number>(0);
  const [latestPowerAc, setLatestPowerAc] = useState<number>(0);
  const [latestPowerFan, setLatestPowerFan] = useState<number>(0);
  const [latestPowerBase, setLatestPowerBase] = useState<number>(0);
  const [latestEnergyBase, setLatestEnergyBase] = useState<number>(0);

  useEffect(() => {
    hvacStateRef.current = hvacState;
  }, [hvacState]);

  useEffect(() => {
    pendingControlRef.current = pendingControl;
  }, [pendingControl]);

  useEffect(() => {
    controlReadyRef.current = isControlStateReady;
  }, [isControlStateReady]);

  useEffect(() => {
    if (!toast) return;
    const timeout = window.setTimeout(() => setToast(null), 3500);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  const showToast = useCallback((type: ToastMessage['type'], message: string) => {
    setToast({ id: Date.now(), type, message });
  }, []);

  const postRemoteControl = useCallback(async (nextState: HVACState, requestedAt: string) => {
    const payload: RemoteControlPayload = {
      device_id: 'indoor-01',
      power: nextState.power,
      temp: nextState.targetTemp,
      operationMode: nextState.mode,
      fanPower: nextState.fanSpeed,
      co2Max: nextState.co2Max,
      humidityMax: nextState.humidityMax,
      clientId,
      requestedAt,
    };
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 6000);

    try {
      const response = await fetch('/api/remote-control', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`Remote control request failed: ${response.status}`);
      }

      const result: RemoteControlResponse = await response.json();
      return remoteToHVACState(result.command);
    } catch (error) {
      console.error(error);
      throw error;
    } finally {
      window.clearTimeout(timeout);
    }
  }, [clientId]);

  const sendRemoteControl = useCallback(async (getNextState: (state: HVACState) => HVACState) => {
    const previousState = hvacStateRef.current;
    const baseState = pendingControlRef.current?.desiredState ?? previousState;
    const desiredState = getNextState(baseState);
    const fields = CONTROL_FIELDS.filter(field => previousState[field] !== desiredState[field]);
    const commandId = commandSequenceRef.current + 1;
    commandSequenceRef.current = commandId;

    if (fields.length === 0) {
      pendingControlRef.current = null;
      setPendingControl(null);
      return;
    }

    const nextPendingControl = {
      commandId,
      previousState,
      desiredState,
      fields,
    };
    pendingControlRef.current = nextPendingControl;
    setPendingControl(nextPendingControl);

    try {
      const officialState = await postRemoteControl(desiredState, new Date().toISOString());
      if (pendingControlRef.current?.commandId !== commandId) return;

      setHvacState(officialState);
      pendingControlRef.current = null;
      setPendingControl(null);
    } catch {
      if (pendingControlRef.current?.commandId !== commandId) return;

      setHvacState(previousState);
      pendingControlRef.current = null;
      setPendingControl(null);
      showToast('error', 'Kết nối tới thiết bị thất bại');
    }
  }, [postRemoteControl, showToast]);

  // --- DATABASE TELEMETRY ---
  useEffect(() => {
    const updateReading = (reading: SensorReading, nextValue: number | null): SensorReading => {
      if (nextValue === null || Number.isNaN(nextValue)) {
        return reading;
      }

      return {
        ...reading,
        value: nextValue,
        status: getStatus(reading.id, nextValue),
        trend: reading.value === 0 ? 0 : ((nextValue - reading.value) / reading.value) * 100,
      };
    };

    const fetchTelemetry = async () => {
      try {
        const response = await fetch('/api/telemetry');
        if (!response.ok) {
          throw new Error(`Telemetry request failed: ${response.status}`);
        }

        const telemetry: TelemetryResponse = await response.json();
        setHistory(telemetry.history);
        if (telemetry.latest) {
          setLatestPower(telemetry.latest.power ?? 0);
          setLatestEnergy(telemetry.latest.energy ?? 0);
          setLatestPowerAc(telemetry.latest.power_ac ?? 0);
          setLatestPowerFan(telemetry.latest.power_fan ?? 0);
          setLatestPowerBase(telemetry.latest.power_base ?? 0);
          setLatestEnergyBase(telemetry.latest.energy_base ?? 0);
        }
        if (telemetry.zoneManager) {
          setZoneManager(telemetry.zoneManager);
        }
        if (telemetry.controlState) {
          const incomingState = remoteToHVACState(telemetry.controlState);
          const incomingRevision = getControlRevision(telemetry.controlState);
          const isNewRevision = lastControlRevisionRef.current !== incomingRevision;
          const isExternalChange = telemetry.controlState.lastModifiedBy !== clientId;
          const wasReady = controlReadyRef.current;

          setHvacState(prevState => {
            const pending = pendingControlRef.current;
            if (!pending) return incomingState;

            return CONTROL_FIELDS.reduce<HVACState>((nextState, field) => {
              if (pending.fields.includes(field)) {
                return nextState;
              }

              return {
                ...nextState,
                [field]: incomingState[field],
              };
            }, prevState);
          });

          if (isNewRevision && wasReady && isExternalChange) {
            showToast('info', `${formatClientLabel(telemetry.controlState.lastModifiedBy)} vừa đổi nhiệt độ`);
          }

          lastControlRevisionRef.current = incomingRevision;
        }
        if (!controlReadyRef.current) {
          controlReadyRef.current = true;
          setIsControlStateReady(true);
        }
        setReadings(prev => prev.map(reading => {
          if (reading.id === 'temp') return updateReading(reading, telemetry.latest.temperature);
          if (reading.id === 'humidity') return updateReading(reading, telemetry.latest.humidity);
          if (reading.id === 'co2') return updateReading(reading, telemetry.latest.co2);
          if (reading.id === 'pm25') return updateReading(reading, telemetry.latest.dust);
          return reading;
        }));
        setLatestValveAngle(telemetry.latest.valve_angle ?? 0);
      } catch (error) {
        console.error(error);
      }
    };

    fetchTelemetry();
    const interval = window.setInterval(fetchTelemetry, 2000);

    return () => window.clearInterval(interval);
  }, [clientId, showToast]);

  // --- WEATHER ---
  useEffect(() => {
    const fetchHanoiWeather = async () => {
      try {
        const params = new URLSearchParams({
          latitude: '21.0245',
          longitude: '105.8412',
          current: 'temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m',
          daily: 'temperature_2m_max,temperature_2m_min,precipitation_probability_max',
          timezone: 'Asia/Bangkok',
          forecast_days: '1',
        });
        const response = await fetch(`https://api.open-meteo.com/v1/forecast?${params.toString()}`);
        if (!response.ok) {
          throw new Error(`Weather request failed: ${response.status}`);
        }

        const weather = await response.json();
        setHanoiWeather({
          temperature: weather.current.temperature_2m,
          apparentTemperature: weather.current.apparent_temperature,
          humidity: weather.current.relative_humidity_2m,
          windSpeed: weather.current.wind_speed_10m,
          weatherCode: weather.current.weather_code,
          minTemp: weather.daily.temperature_2m_min[0],
          maxTemp: weather.daily.temperature_2m_max[0],
          precipitationProbability: weather.daily.precipitation_probability_max[0],
        });
      } catch (error) {
        console.error(error);
      }
    };

    fetchHanoiWeather();
    const interval = window.setInterval(fetchHanoiWeather, 2 * 60 * 60 * 1000);

    return () => window.clearInterval(interval);
  }, []);

  // Derived stats
  const activeAlerts = useMemo(() => readings.filter(r => r.status !== 'good').length, [readings]);
  const displayHvacState = pendingControl?.desiredState ?? hvacState;
  const pendingFields = useMemo(() => {
    return pendingControl?.fields.reduce<Partial<Record<ControlField, boolean>>>((fields, field) => {
      fields[field] = true;
      return fields;
    }, {}) ?? {};
  }, [pendingControl]);

  return (
    <div className="min-h-screen text-slate-100 overflow-x-clip selection:bg-blue-500/20">
      {/* --- TOP BAR --- */}
      <header className="fixed top-0 left-0 right-0 h-16 bg-[#080c14]/80 backdrop-blur-md border-b border-slate-900/80 z-50 px-4 md:px-8 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img src={mainLogo} alt="HVAC Sentinel Logo" className="h-9 object-contain" />
          <div className="hidden sm:flex flex-col">
            <span className="text-xs font-black uppercase tracking-widest bg-gradient-to-r from-emerald-400 via-teal-300 to-blue-500 bg-clip-text text-transparent">HVAC Sentinel</span>
            <span className="text-[8px] font-bold text-slate-500 uppercase tracking-tight">AI-IoT Optimization Platform</span>
          </div>
        </div>

        {/* System Status Indicators */}
        <div className="flex items-center gap-4">
          <div className="hidden md:flex items-center gap-4 border-r border-slate-800 pr-6 mr-2">
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse animate-glow-emerald" />
              <span className="text-[9px] font-black uppercase text-slate-400">Node ESP32: Online</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse animate-glow-emerald" />
              <span className="text-[9px] font-black uppercase text-slate-400">Broker MQTT: Connected</span>
            </div>
            <div className="flex flex-col items-end pl-2">
              <span className="text-[9px] text-slate-500 uppercase font-bold tracking-widest">Uptime</span>
              <span className="text-[10px] font-mono text-slate-300 font-bold">12d 04h 22m</span>
            </div>
          </div>

          <div className="relative cursor-pointer">
            <Bell className="w-4 h-4 text-slate-400 hover:text-slate-200 transition-colors" />
            {activeAlerts > 0 && (
              <span className="absolute -top-1 -right-1 w-2 h-2 bg-red-500 rounded-full border border-[#080c14] animate-pulse animate-glow-red" />
            )}
          </div>
          <div className="w-7 h-7 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center overflow-hidden">
             <User className="w-4 h-4 text-slate-400" />
          </div>
        </div>
      </header>

      {/* --- MAIN CONTENT --- */}
      <main className="pt-24 pb-8 px-4 md:px-8 max-w-[1600px] mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Dashboard Left Section: Metrics & Charts */}
          <div className="lg:col-span-8 space-y-6">
            
            {/* Header info */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-black tracking-tight text-white uppercase">Tổng quan hệ thống</h2>
                <p className="text-slate-500 text-xs mt-0.5">Khu vực: Phòng Server Hall A-42 • Tầng 12</p>
              </div>
              <div className="flex gap-2">
                <button className="flex items-center gap-2 px-3 py-1.5 bg-slate-900/40 hover:bg-slate-800 border border-slate-850 hover:border-slate-700 rounded-xl text-[10px] font-bold text-slate-300 transition-colors cursor-pointer">
                  <History className="w-3.5 h-3.5" />
                  Nhật ký Lỗi
                </button>
                <button className="flex items-center gap-2 px-3 py-1.5 bg-slate-900/40 hover:bg-slate-800 border border-slate-850 hover:border-slate-700 rounded-xl text-[10px] font-bold text-slate-300 transition-colors cursor-pointer">
                  <Maximize2 className="w-3.5 h-3.5" />
                  Toàn màn hình
                </button>
              </div>
            </div>

            {/* Metric Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-5 gap-4">
              <MetricCard reading={readings[0]} icon={Thermometer} />
              <MetricCard reading={readings[1]} icon={Droplets} />
              <MetricCard reading={readings[2]} icon={Wind} />
              <MetricCard reading={readings[3]} icon={Activity} />
              <MetricCard reading={{id: 'valve_angle', name: 'Độ mở Van gió', value: latestValveAngle, unit: '°', status: 'good', trend: 0 }} icon={RotateCw} />
            </div>

            {/* Main Visualizations */}
            <div className="grid grid-cols-1 gap-6">
              <RealTimeChart data={history} />
            </div>

            {/* Secondary Intel */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
               <div className="glass-panel rounded-2xl p-5 border border-slate-800/85 shadow-xl flex flex-col justify-between min-h-[250px]">
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Hiệu năng Tối ưu AI</h4>
                      <span className="flex items-center gap-1 text-[8px] font-black px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse animate-glow-emerald" />
                        AI COORD ACTIVE
                      </span>
                    </div>

                    <div className="space-y-3.5">
                      {/* Big Savings Metric */}
                      <div className="flex items-center gap-4 bg-emerald-500/5 p-3.5 rounded-xl border border-emerald-500/10">
                        <div className="w-10 h-10 rounded-xl bg-emerald-500/15 flex items-center justify-center text-emerald-400 font-extrabold text-lg">
                          🍃
                        </div>
                        <div>
                          <p className="text-[9px] text-emerald-400 font-black uppercase tracking-wider">AI tiết kiệm điện năng</p>
                          <p className="text-2xl font-black font-mono text-emerald-400 leading-none mt-1">
                            {latestEnergyBase > latestEnergy 
                              ? (((latestEnergyBase - latestEnergy) / latestEnergyBase) * 100).toFixed(1)
                              : '0.0'}%
                          </p>
                          <p className="text-[9px] text-slate-500 font-bold mt-1">
                            Lượng điện giảm: {Math.max(0, latestEnergyBase - latestEnergy).toFixed(3)} kWh
                          </p>
                        </div>
                      </div>

                      {/* Savings Breakdown */}
                      <div className="grid grid-cols-2 gap-3 text-xs font-semibold pt-1">
                        <div className="border-r border-slate-800 pr-2">
                          <p className="text-[8px] text-slate-500 font-bold uppercase tracking-wider">Chi phí đã giảm</p>
                          <p className="text-sm font-extrabold text-emerald-400 mt-0.5">
                            - {Math.max(0, (latestEnergyBase - latestEnergy) * 2500).toLocaleString('vi-VN', { maximumFractionDigits: 0 })} VNĐ
                          </p>
                        </div>
                        <div className="pl-2">
                          <p className="text-[8px] text-slate-500 font-bold uppercase tracking-wider">Giảm phát thải CO2</p>
                          <p className="text-sm font-extrabold text-slate-300 mt-0.5">
                            - {Math.max(0, (latestEnergyBase - latestEnergy) * 0.5).toFixed(3)} kg
                          </p>
                        </div>
                      </div>

                      {/* Current active policy */}
                      <div className="flex justify-between items-center border-t border-slate-800/80 pt-2.5 text-xs">
                        <span className="text-slate-400 font-semibold text-[10px]">Chế độ vận hành của AI</span>
                        <span className="text-[8px] font-black uppercase text-slate-300 bg-slate-900 border border-slate-800 px-2.5 py-0.5 rounded-full">
                          {zoneManager?.currentPolicy === 'working_hours' && '💼 Giờ làm việc'}
                          {zoneManager?.currentPolicy === 'night_eco' && '🌙 Ngủ đêm ECO'}
                          {zoneManager?.currentPolicy === 'eco_standby' && '🍃 Chờ tiết kiệm'}
                          {zoneManager?.currentPolicy === 'manual' && '👤 Thủ công'}
                        </span>
                      </div>

                      {/* AI recommendation */}
                      <div className="p-2.5 rounded-xl bg-slate-950/40 border border-slate-900 text-[10px] text-slate-400 leading-relaxed font-semibold">
                        <span className="font-black text-slate-500 block mb-0.5 uppercase text-[8px] tracking-wider">AI Khuyến cáo:</span>
                        {zoneManager?.aiRecommendation || 'Đang phân tích hoạt động phòng...'}
                      </div>
                    </div>
                  </div>
               </div>

               <div className="glass-panel rounded-2xl p-5 border border-slate-800/85 shadow-xl flex flex-col justify-between min-h-[280px]">
                  <div className="space-y-4">
                    <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center justify-between">
                      <span>Điện năng tiêu thụ (Mô phỏng)</span>
                      <span className="flex items-center gap-1 text-[8px] font-black px-1.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
                        <span className="w-1 h-1 rounded-full bg-blue-500 animate-pulse animate-glow-blue" />
                        Đang giám sát
                      </span>
                    </h4>
                    
                    {/* Real-time Load & Consumption */}
                    <div className="grid grid-cols-2 gap-4 bg-slate-950/50 p-3.5 rounded-xl border border-slate-900">
                      <div>
                        <p className="text-[8px] text-slate-500 uppercase font-bold tracking-wider">Tổng tiêu thụ (AI)</p>
                        <p className="text-xl font-extrabold font-mono text-slate-100 tracking-tight leading-none mt-1">
                          {latestEnergy.toFixed(3)}
                          <span className="text-xs text-slate-500 ml-1 font-bold">kWh</span>
                        </p>
                        <p className="text-[8px] text-slate-500 font-bold tracking-tighter leading-none mt-1">
                          Tạm tính: {(latestEnergy * 2500).toLocaleString('vi-VN', { maximumFractionDigits: 0 })} VNĐ
                        </p>
                      </div>
                      <div>
                        <p className="text-[8px] text-slate-500 uppercase font-bold tracking-wider">Công suất tức thì</p>
                        <p className="text-xl font-extrabold font-mono text-blue-400 tracking-tight leading-none mt-1">
                          {latestPower >= 1000 ? (latestPower / 1000).toFixed(2) : latestPower.toFixed(0)}
                          <span className="text-xs text-slate-500 ml-1 font-bold">{latestPower >= 1000 ? 'kW' : 'W'}</span>
                        </p>
                        <span className={cn(
                          "inline-flex items-center gap-0.5 text-[8px] font-black px-1.5 py-0.5 rounded-full mt-1.5 border",
                          latestPower < 50 
                            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                            : latestPower < 500
                            ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                            : 'bg-orange-500/10 text-orange-400 border-orange-500/20'
                        )}>
                          {latestPower < 50 ? 'Chờ/Tiết kiệm' : latestPower < 500 ? 'Tải Trung bình' : 'Tải Cao'}
                        </span>
                      </div>
                    </div>

                    {/* Breakdown section */}
                    <div className="space-y-1.5">
                      <span className="text-[8px] text-slate-500 font-bold uppercase tracking-wider block">Phân rã công suất mô phỏng</span>
                      <div className="grid grid-cols-3 gap-2">
                        <div className="bg-slate-950/30 border border-slate-900 rounded-lg p-2 text-center">
                          <p className="text-[8px] text-slate-500 font-bold uppercase tracking-wider">Điều hòa (AC)</p>
                          <p className="text-xs font-black font-mono text-slate-300 mt-0.5">{latestPowerAc.toFixed(0)} W</p>
                        </div>
                        <div className="bg-slate-950/30 border border-slate-900 rounded-lg p-2 text-center">
                          <p className="text-[8px] text-slate-500 font-bold uppercase tracking-wider">Quạt gió (Fan)</p>
                          <p className="text-xs font-black font-mono text-slate-300 mt-0.5">{latestPowerFan.toFixed(0)} W</p>
                        </div>
                        <div className="bg-slate-950/30 border border-slate-900 rounded-lg p-2 text-center">
                          <p className="text-[8px] text-slate-500 font-bold uppercase tracking-wider font-semibold">Hệ thống (Stby)</p>
                          <p className="text-xs font-black font-mono text-slate-300 mt-0.5">5 W</p>
                        </div>
                      </div>
                    </div>

                    {/* Baseline Comparison section */}
                    <div className="border-t border-slate-800/80 pt-3 space-y-2">
                      <div className="flex justify-between items-center">
                        <span className="text-[8px] text-slate-500 font-bold uppercase tracking-wider">So sánh hiệu quả với Baseline</span>
                        {latestEnergyBase > 0 && latestEnergyBase > latestEnergy ? (
                          <span className="inline-flex items-center gap-0.5 text-[8px] font-black text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-full border border-emerald-500/20">
                            🍃 AI tiết kiệm: {(((latestEnergyBase - latestEnergy) / latestEnergyBase) * 100).toFixed(1)}%
                          </span>
                        ) : (
                          <span className="text-[8px] text-slate-500 font-bold italic">Đang phân tích...</span>
                        )}
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4 text-xs font-semibold">
                        <div className="border-r border-slate-800 pr-2">
                          <p className="text-[8px] text-emerald-400 font-bold uppercase tracking-wider">Hệ thống AI Tối ưu</p>
                          <p className="text-xs font-black font-mono text-slate-200 mt-0.5">{latestEnergy.toFixed(3)} kWh</p>
                          <p className="text-[8px] text-slate-500 font-bold">~{(latestEnergy * 2500).toLocaleString('vi-VN', { maximumFractionDigits: 0 })} VNĐ</p>
                        </div>
                        <div className="pl-2">
                          <p className="text-[8px] text-slate-500 font-bold uppercase tracking-wider">Baseline (Không tối ưu)</p>
                          <p className="text-xs font-black font-mono text-slate-400 mt-0.5">{latestEnergyBase.toFixed(3)} kWh</p>
                          <p className="text-[8px] text-slate-500 font-bold">~{(latestEnergyBase * 2500).toLocaleString('vi-VN', { maximumFractionDigits: 0 })} VNĐ</p>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  {/* Sparkline chart at the very bottom */}
                  <div className="flex items-center justify-between pt-3 border-t border-slate-800/80 mt-3">
                    <span className="text-[8px] text-slate-500 font-bold uppercase tracking-wider">Biểu đồ tải (7 điểm gần nhất)</span>
                    <div className="w-32 h-8 flex items-end gap-0.5">
                      {(() => {
                        const lastPowerPoints = history.slice(-7);
                        const maxPower = Math.max(...lastPowerPoints.map(p => p.power ?? 0), 100);
                        return lastPowerPoints.map((pt, i) => {
                          const power = pt.power ?? 0;
                          const heightPercent = maxPower > 0 ? (power / maxPower) * 100 : 10;
                          return (
                            <div 
                              key={i} 
                              className={`flex-1 rounded-t-sm transition-all duration-500 ${
                                power < 50 ? 'bg-emerald-500/50' : power < 500 ? 'bg-blue-500/60' : 'bg-blue-400'
                              }`}
                              style={{ height: `${Math.max(10, heightPercent)}%` }}
                              title={`AI: ${power.toFixed(0)}W | Baseline: ${(pt.power_base ?? 0).toFixed(0)}W`}
                            />
                          );
                        });
                      })()}
                    </div>
                  </div>
               </div>
            </div>
          </div>

          {/* Dashboard Right Section: Controls & Status */}
          <div className="lg:col-span-4 space-y-6">
            
            {isControlStateReady ? (
              <ControlPanel
                state={displayHvacState}
                pendingFields={pendingFields}
                onControlChange={sendRemoteControl}
              />
            ) : (
              <div className="glass-panel rounded-2xl p-6 border border-slate-850 shadow-2xl h-full min-h-[560px] flex flex-col">
                <div className="flex items-center justify-between mb-6">
                  <div>
                    <h3 className="text-xs font-bold uppercase tracking-widest text-slate-500">AC UNIT 01</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <div className="w-1.5 h-1.5 rounded-full bg-slate-600 animate-pulse" />
                      <span className="text-[10px] font-bold text-slate-500 uppercase">Đang tải cấu hình...</span>
                    </div>
                  </div>
                  <div className="w-11 h-11 rounded-xl bg-slate-900 border border-slate-800 animate-pulse" />
                </div>
                <div className="flex-1 flex flex-col items-center justify-center gap-8">
                  <div className="w-full aspect-square max-w-[190px] rounded-full border-4 border-slate-800 bg-slate-900/20 animate-pulse" />
                  <div className="w-full space-y-3">
                    <div className="h-3 w-32 mx-auto bg-slate-900 rounded animate-pulse" />
                    <div className="grid grid-cols-3 gap-3">
                      {[0, 1, 2].map((item) => (
                        <div key={item} className="h-16 rounded-xl bg-slate-900/40 border border-slate-800 animate-pulse" />
                      ))}
                    </div>
                  </div>
                  <div className="w-full space-y-3">
                    <div className="h-3 w-24 bg-slate-900 rounded animate-pulse" />
                    <div className="h-10 rounded-xl bg-slate-900/40 border border-slate-800 animate-pulse" />
                  </div>
                </div>
              </div>
            )}

            {/* Weather */}
            <div className="glass-panel rounded-2xl p-5 border border-slate-800/85 shadow-xl">
               <div className="flex items-center justify-between mb-4">
                  <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Thời tiết Hà Nội</h4>
                  <div className="flex items-center gap-1 text-[9px] text-slate-500 font-bold uppercase tracking-wider">
                    <MapPin className="w-3 h-3" />
                    Hôm nay
                  </div>
               </div>
                {hanoiWeather ? (
                  <div className="space-y-3.5">
                    {[
                      { item: 'Nhiệt độ Hiện tại', status: `${hanoiWeather.temperature.toFixed(1)}°C`, color: 'text-blue-400' },
                      { item: 'Trạng thái', status: getWeatherLabel(hanoiWeather.weatherCode), color: 'text-sky-400' },
                      { item: 'Cảm giác thực tế', status: `${hanoiWeather.apparentTemperature.toFixed(1)}°C`, color: 'text-slate-300' },
                    ].map((step) => (
                      <div key={step.item} className="flex justify-between items-center border-b border-slate-900 pb-2">
                         <span className="text-xs text-slate-400 font-semibold">{step.item}</span>
                         <span className={cn("text-[10px] font-black uppercase tracking-wider", step.color)}>{step.status}</span>
                      </div>
                    ))}
                    <div className="grid grid-cols-2 gap-x-4 gap-y-3">
                      {[
                        { label: 'Độ ẩm', value: `${hanoiWeather.humidity}%`, icon: Droplets },
                        { label: 'Tốc độ Gió', value: `${hanoiWeather.windSpeed.toFixed(1)} km/h`, icon: Wind },
                        { label: 'Cao / Thấp', value: `${hanoiWeather.maxTemp.toFixed(1)} / ${hanoiWeather.minTemp.toFixed(1)}°C`, icon: Thermometer },
                        { label: 'Khả năng mưa', value: `${hanoiWeather.precipitationProbability}%`, icon: CloudRain },
                      ].map((item) => (
                        <div key={item.label} className="flex items-center justify-between gap-2 border-b border-slate-900 pb-2">
                          <div className="flex items-center gap-1 text-slate-500 mb-1">
                            <item.icon className="w-3 h-3" />
                            <span className="text-[8px] font-bold uppercase tracking-wider">{item.label}</span>
                          </div>
                          <p className="text-xs font-mono font-bold text-slate-300">{item.value}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                ) : (
                  <div className="h-28 flex items-center justify-center">
                    <span className="text-xs text-slate-500 font-bold uppercase tracking-wider animate-pulse">Đang tải thời tiết...</span>
                  </div>
                )}
            </div>

            {/* Notification Center */}
            <div className="glass-panel rounded-2xl p-5 border border-slate-800/85 shadow-xl">
               <h4 className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-4">Cảnh báo hệ thống</h4>
               <div className="space-y-4">
                  <AnimatePresence>
                    {activeAlerts > 0 ? (
                      readings.filter(r => r.status !== 'good').map((r) => (
                        <motion.div 
                          key={r.id}
                          initial={{ opacity: 0, x: 20 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: -20 }}
                          className={cn(
                            "p-3 rounded-xl border flex items-start gap-3",
                            r.status === 'critical' 
                              ? "bg-red-500/10 border-red-500/20 text-red-300" 
                              : "bg-amber-500/10 border-amber-500/20 text-amber-300"
                          )}
                        >
                           <AlertTriangle className={cn("w-4 h-4 shrink-0 mt-0.5", r.status === 'critical' ? "text-red-400" : "text-amber-400")} />
                           <div className="space-y-1">
                              <p className="text-[10px] font-black uppercase tracking-wider">Phát hiện vượt ngưỡng {r.name}</p>
                              <p className="text-[9px] text-slate-400 leading-normal font-semibold">Giá trị hiện tại là {r.value.toFixed(1)}{r.unit} đã vượt quá giới hạn an toàn quy định.</p>
                           </div>
                        </motion.div>
                      ))
                    ) : (
                      <div className="text-center py-6">
                        <p className="text-[9px] text-slate-500 uppercase font-black tracking-wider">Hệ thống đang vận hành ổn định</p>
                      </div>
                    )}
                  </AnimatePresence>
               </div>
            </div>

          </div>
        </div>
      </main>
      <AnimatePresence>
        {toast && (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 16 }}
            className={cn(
              "fixed bottom-6 right-6 z-[60] max-w-sm rounded-xl border px-4 py-3 shadow-2xl flex items-start gap-3 glass-panel",
              toast.type === 'error'
                ? "border-red-500/30 text-red-400 shadow-[0_4px_20px_rgba(239,68,68,0.15)] animate-glow-red"
                : "border-blue-500/30 text-blue-400 shadow-[0_4px_20px_rgba(59,130,246,0.15)] animate-glow-blue"
            )}
          >
            <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
            <p className="text-xs font-black uppercase tracking-wider">{toast.message}</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

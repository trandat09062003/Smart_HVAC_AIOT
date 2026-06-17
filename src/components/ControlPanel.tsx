import React from 'react';
import { Power, Wind, Sun, Snowflake, Fan, Thermometer, LoaderCircle, Droplets, Plus, Minus } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { HVACState } from '../types';
import { cn } from '../lib/utils';

interface ControlPanelProps {
  state: HVACState;
  pendingFields: Partial<Record<keyof HVACState, boolean>>;
  onControlChange: (getNextState: (state: HVACState) => HVACState) => void;
}

export const ControlPanel: React.FC<ControlPanelProps> = ({ state, pendingFields, onControlChange }) => {
  const updateControl = (getNextState: (state: HVACState) => HVACState) => {
    onControlChange(getNextState);
  };

  const togglePower = () => updateControl(prev => ({ ...prev, power: !prev.power }));
  
  const setMode = (mode: HVACState['mode']) => updateControl(prev => ({ ...prev, mode }));
  
  const setFanSpeed = (fanSpeed: HVACState['fanSpeed']) => updateControl(prev => ({ ...prev, fanSpeed }));

  const incrementTemp = () => {
    if (state.targetTemp < 30) {
      updateControl(prev => ({ ...prev, targetTemp: Math.min(30, prev.targetTemp + 0.5) }));
    }
  };

  const decrementTemp = () => {
    if (state.targetTemp > 16) {
      updateControl(prev => ({ ...prev, targetTemp: Math.max(16, prev.targetTemp - 0.5) }));
    }
  };

  const modeColors: Record<string, string> = {
    auto: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
    cool: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
    heat: 'text-orange-400 bg-orange-500/10 border-orange-500/30',
    off: 'text-slate-400 bg-slate-500/10 border-slate-500/30',
  };

  const modeGlows: Record<string, string> = {
    auto: 'shadow-[0_0_30px_rgba(168,85,247,0.2)] border-purple-500/40',
    cool: 'shadow-[0_0_30px_rgba(59,130,246,0.2)] border-blue-500/40',
    heat: 'shadow-[0_0_30px_rgba(249,115,22,0.2)] border-orange-500/40',
    off: 'shadow-none border-slate-800',
  };

  const isPending = Object.values(pendingFields).some(Boolean);
  const isAutoMode = state.mode === 'auto';

  return (
    <div className="glass-panel rounded-2xl p-6 border shadow-2xl h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">ĐIỀU HÒA GIẢ LẬP</h3>
          <div className="flex items-center gap-2 mt-1">
            <div className={cn("w-1.5 h-1.5 rounded-full", state.power ? "bg-emerald-500 animate-pulse animate-glow-emerald" : "bg-slate-500")} />
            <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider">
              {isPending ? 'Đang đồng bộ...' : state.power ? 'Hệ thống Sẵn sàng' : 'Chế độ Chờ'}
            </span>
          </div>
        </div>
        <button
          onClick={togglePower}
          className={cn(
            "p-3 rounded-xl transition-all duration-300 ring-4 cursor-pointer",
            state.power 
              ? "bg-emerald-500 ring-emerald-500/20 text-white shadow-lg shadow-emerald-500/20" 
              : "bg-slate-800 ring-slate-800/20 text-slate-500"
          )}
        >
          <Power className="w-4 h-4" />
        </button>
      </div>

      <div className={cn("flex-1 space-y-6 transition-all duration-500", !state.power && "opacity-20 grayscale pointer-events-none")}>
        
        {/* Visual Temperature Controller */}
        <div className="relative flex flex-col items-center py-2">
          {/* Temperature Circle Outer ring */}
          <div className={cn(
            "w-full aspect-square max-w-[190px] rounded-full border-4 border-slate-800 bg-slate-900/30 flex flex-col items-center justify-center transition-all duration-500 relative",
            pendingFields.targetTemp && "opacity-60",
            state.power && modeGlows[state.mode]
          )}>
            <div className="text-slate-400 mb-1 flex items-center gap-1">
              <Thermometer className="w-3.5 h-3.5" />
              <span className="text-[9px] font-black uppercase tracking-wider">
                {isAutoMode ? 'AI Target Temp' : 'Manual Set Temp'}
              </span>
            </div>
            
            <div className="relative">
              <AnimatePresence mode="wait">
                <motion.div
                  key={state.targetTemp}
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 1.1 }}
                  className="text-5xl font-extrabold font-mono text-white tracking-tighter tabular-nums leading-none"
                >
                  {state.targetTemp.toFixed(1)}
                </motion.div>
              </AnimatePresence>
              {pendingFields.targetTemp && (
                <LoaderCircle className="absolute -right-6 top-1 w-5 h-5 text-blue-400 animate-spin" />
              )}
            </div>
            
            <span className="text-sm font-bold text-slate-400 mt-1">°C</span>

            {/* Circular Incrementor/Decrementor buttons on the sides */}
            {!isAutoMode && (
              <>
                <button 
                  onClick={decrementTemp}
                  className="absolute left-[-20px] top-1/2 -translate-y-1/2 w-10 h-10 rounded-full border border-slate-800 bg-slate-900 hover:bg-slate-800 hover:border-slate-700 text-slate-300 flex items-center justify-center cursor-pointer shadow-lg transition-colors"
                  title="Giảm nhiệt độ"
                >
                  <Minus className="w-4 h-4" />
                </button>
                <button 
                  onClick={incrementTemp}
                  className="absolute right-[-20px] top-1/2 -translate-y-1/2 w-10 h-10 rounded-full border border-slate-800 bg-slate-900 hover:bg-slate-800 hover:border-slate-700 text-slate-300 flex items-center justify-center cursor-pointer shadow-lg transition-colors"
                  title="Tăng nhiệt độ"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </>
            )}
          </div>
        </div>

        {/* Safety Thresholds Displays */}
        <div className="grid grid-cols-2 gap-3">
          {/* CO2 Threshold Card */}
          <div className="bg-slate-950/40 border border-slate-800/80 rounded-xl p-3 flex flex-col items-center justify-between text-center min-h-[105px]">
            <div className="text-emerald-400 flex items-center gap-1">
              <Wind className="w-3.5 h-3.5" />
              <span className="text-[9px] font-black uppercase tracking-wider">Ngưỡng CO2</span>
            </div>
            
            <div className="flex flex-col items-center justify-center my-1.5">
              <p className="text-base font-extrabold font-mono text-slate-200 leading-none tabular-nums">
                {state.co2Max ?? 800} <span className="text-[10px] text-slate-500 font-bold">ppm</span>
              </p>
              <span className="text-[8px] text-emerald-400 font-bold mt-1 bg-emerald-500/10 px-1.5 py-0.5 rounded-full border border-emerald-500/20 flex items-center gap-0.5">
                <span className="w-1 h-1 rounded-full bg-emerald-500 animate-pulse" />
                AI Auto
              </span>
            </div>
            <span className="text-[7px] text-slate-500 font-bold uppercase tracking-tighter leading-none">Bật quạt nếu vượt quá</span>
          </div>

          {/* Humidity Threshold Card */}
          <div className="bg-slate-950/40 border border-slate-800/80 rounded-xl p-3 flex flex-col items-center justify-between text-center min-h-[105px]">
            <div className="text-blue-400 flex items-center gap-1">
              <Droplets className="w-3.5 h-3.5" />
              <span className="text-[9px] font-black uppercase tracking-wider">Ngưỡng Độ Ẩm</span>
            </div>
            
            <div className="flex flex-col items-center justify-center my-1.5">
              <p className="text-base font-extrabold font-mono text-slate-200 leading-none tabular-nums">
                {state.humidityMax ?? 60}.0<span className="text-[10px] text-slate-500 font-bold">%</span>
              </p>
              <span className="text-[8px] text-blue-400 font-bold mt-1 bg-blue-500/10 px-1.5 py-0.5 rounded-full border border-blue-500/20 flex items-center gap-0.5">
                <span className="w-1 h-1 rounded-full bg-blue-500 animate-pulse" />
                AI Auto
              </span>
            </div>
            <span className="text-[7px] text-slate-500 font-bold uppercase tracking-tighter leading-none">Bật quạt nếu vượt quá</span>
          </div>
        </div>

        {/* HVAC Operation Mode Selection */}
        <div className="space-y-3">
          <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest block text-center">Chế độ vận hành</span>
          
          <div className="flex gap-2 p-1 bg-slate-950/50 rounded-xl border border-slate-800">
            <button
              onClick={() => setMode('auto')}
              className={cn(
                "flex-1 py-1.5 rounded-lg text-[9px] font-extrabold uppercase transition-all cursor-pointer",
                isAutoMode 
                  ? "bg-purple-600/20 text-purple-400 border border-purple-500/30 shadow-[0_0_10px_rgba(168,85,247,0.1)]" 
                  : "text-slate-500 hover:text-slate-400 border border-transparent"
              )}
            >
              Auto AI
            </button>
            <button
              onClick={() => {
                if (isAutoMode) {
                  setMode('cool'); // Mặc định chọn cooling khi chuyển sang thủ công
                }
              }}
              className={cn(
                "flex-1 py-1.5 rounded-lg text-[9px] font-extrabold uppercase transition-all cursor-pointer",
                !isAutoMode 
                  ? "bg-slate-800 text-slate-200 border border-slate-700" 
                  : "text-slate-500 hover:text-slate-400 border border-transparent"
              )}
            >
              Thủ công
            </button>
          </div>

          {/* Sub-modes for manual control */}
          <AnimatePresence>
            {!isAutoMode && (
              <motion.div 
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="overflow-hidden"
              >
                <div className="grid grid-cols-3 gap-2 pt-1">
                  {[
                    { id: 'cool', icon: Snowflake, label: 'Làm lạnh', activeClass: 'text-blue-400 bg-blue-500/10 border-blue-500/30 shadow-[0_0_15px_rgba(59,130,246,0.1)]' },
                    { id: 'heat', icon: Sun, label: 'Làm nóng', activeClass: 'text-orange-400 bg-orange-500/10 border-orange-500/30 shadow-[0_0_15px_rgba(249,115,22,0.1)]' },
                    { id: 'off', icon: Power, label: 'Tắt HVAC', activeClass: 'text-slate-400 bg-slate-500/10 border-slate-500/30' },
                  ].map((m) => {
                    const isActive = state.mode === m.id;
                    return (
                      <button
                        key={m.id}
                        onClick={() => setMode(m.id as HVACState['mode'])}
                        className={cn(
                          "flex flex-col items-center gap-1.5 py-2 px-1 rounded-xl border transition-all text-center cursor-pointer",
                          isActive 
                            ? m.activeClass 
                            : "bg-slate-900/30 border-slate-800 text-slate-500 hover:border-slate-700"
                        )}
                      >
                        <m.icon className="w-3.5 h-3.5" />
                        <span className="text-[8px] uppercase font-extrabold tracking-tight">{m.label}</span>
                      </button>
                    );
                  })}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Fan Speed - Visual Slider feel */}
        <div className="space-y-3">
          <div className="flex justify-between items-center px-1">
             <span className="text-[9px] font-black text-slate-400 uppercase tracking-widest">Quạt thông gió</span>
             <Fan 
               className={cn("w-3.5 h-3.5 text-slate-500", state.power && state.fanSpeed !== 'off' && "animate-spin")} 
               style={{ animationDuration: state.fanSpeed === 'auto' ? '2.5s' : '1.2s' }} 
             />
          </div>
          
          <div className="flex gap-2 p-1 bg-slate-950/50 rounded-xl border border-slate-800">
            <button
              onClick={() => setFanSpeed('auto')}
              className={cn(
                "flex-1 py-1.5 rounded-lg text-[9px] font-extrabold uppercase transition-all cursor-pointer",
                state.fanSpeed === 'auto' 
                  ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shadow-[0_0_10px_rgba(16,185,129,0.1)]" 
                  : "text-slate-500 hover:text-slate-400 border border-transparent"
              )}
            >
              Auto
            </button>
            <button
              onClick={() => {
                if (state.fanSpeed === 'auto') {
                  setFanSpeed('on');
                }
              }}
              className={cn(
                "flex-1 py-1.5 rounded-lg text-[9px] font-extrabold uppercase transition-all cursor-pointer",
                state.fanSpeed !== 'auto' 
                  ? "bg-slate-800 text-slate-200 border border-slate-700" 
                  : "text-slate-500 hover:text-slate-400 border border-transparent"
              )}
            >
              Thủ công
            </button>
          </div>

          <AnimatePresence>
            {state.fanSpeed !== 'auto' && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="overflow-hidden"
              >
                <div className="flex gap-2 pt-1">
                  {[
                    { id: 'on', label: 'Bật quạt (ON)', activeClass: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 shadow-[0_0_10px_rgba(16,185,129,0.1)]' },
                    { id: 'off', label: 'Tắt quạt (OFF)', activeClass: 'bg-slate-800 text-slate-300 border border-slate-700' }
                  ].map((item) => {
                    const isActive = state.fanSpeed === item.id;
                    return (
                      <button
                        key={item.id}
                        onClick={() => setFanSpeed(item.id as HVACState['fanSpeed'])}
                        className={cn(
                          "flex-1 py-2 rounded-xl border text-[8px] font-extrabold uppercase transition-all text-center cursor-pointer",
                          isActive 
                            ? item.activeClass 
                            : "bg-slate-900/30 border-slate-800 text-slate-500 hover:border-slate-750"
                        )}
                      >
                        {item.label}
                      </button>
                    );
                  })}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};


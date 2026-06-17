import React from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { TrendingUp, TrendingDown, LucideIcon, Cpu, Settings } from 'lucide-react';
import { Status, SensorReading } from '../types';
import { cn } from '../lib/utils';

interface MetricCardProps {
  reading: SensorReading;
  icon: LucideIcon;
}

const statusColors: Record<Status, string> = {
  good: 'bg-emerald-500',
  warning: 'bg-amber-500',
  critical: 'bg-red-500',
  active: 'bg-blue-500',
};

const statusBorders: Record<Status, string> = {
  good: 'border-emerald-500/20 hover:border-emerald-500/40',
  warning: 'border-amber-500/20 hover:border-amber-500/40',
  critical: 'border-red-500/40 hover:border-red-500/60 animate-glow-red',
  active: 'border-blue-500/20 hover:border-blue-500/40',
};

const statusTextColors: Record<Status, string> = {
  good: 'text-emerald-400',
  warning: 'text-amber-400',
  critical: 'text-red-400',
  active: 'text-blue-400',
};

const statusBackgrounds: Record<Status, string> = {
  good: 'bg-emerald-500/10',
  warning: 'bg-amber-500/10',
  critical: 'bg-red-500/10',
  active: 'bg-blue-500/10',
};

export const MetricCard: React.FC<MetricCardProps> = ({ reading, icon: Icon }) => {
  const isPhysical = ['temp', 'humidity', 'co2', 'pm25'].includes(reading.id);

  return (
    <motion.div
      layout
      className={cn(
        "relative overflow-hidden glass-panel glass-panel-hover rounded-2xl p-5 border shadow-lg",
        statusBorders[reading.status]
      )}
    >
      {/* Top accent line */}
      <div className={cn("absolute top-0 left-0 right-0 h-1 opacity-80", statusColors[reading.status])} />

      <div className="flex justify-between items-start mb-4">
        <div className="space-y-1">
          <p className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
            {reading.name}
          </p>
          <div className="flex items-center gap-1.5">
            {isPhysical ? (
              <span className="inline-flex items-center gap-1 text-[8px] font-black uppercase text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-1.5 py-0.5 rounded-full">
                <Cpu className="w-2.5 h-2.5" />
                ESP32 Node
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 text-[8px] font-black uppercase text-blue-400 bg-blue-500/10 border border-blue-500/20 px-1.5 py-0.5 rounded-full">
                <Settings className="w-2.5 h-2.5 animate-spin" style={{ animationDuration: '6s' }} />
                Mô phỏng
              </span>
            )}
          </div>
        </div>
        <div className={cn("p-2 rounded-xl border", statusBackgrounds[reading.status], statusBorders[reading.status])}>
          <Icon className={cn("w-4 h-4", statusTextColors[reading.status])} />
        </div>
      </div>

      <div className="flex items-baseline gap-2 mb-2">
        <AnimatePresence mode="popLayout">
          <motion.span
            key={reading.value}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            className="text-3xl md:text-4xl font-extrabold font-mono tracking-tight tabular-nums text-white"
          >
            {reading.value.toFixed(1)}
          </motion.span>
        </AnimatePresence>
        <span className="text-sm text-slate-400 font-semibold">{reading.unit}</span>
      </div>

      <div className="flex items-center gap-2">
        {reading.id !== 'valve_angle' ? (
          <>
            <div className={cn(
              "flex items-center gap-0.5 text-[10px] font-bold px-1.5 py-0.5 rounded",
              reading.trend >= 0 
                ? "text-emerald-400 bg-emerald-500/10 border border-emerald-500/20" 
                : "text-amber-400 bg-amber-500/10 border border-amber-500/20"
            )}>
              <span>{reading.trend >= 0 ? '▲' : '▼'}</span>
              <span>{Math.abs(reading.trend).toFixed(1)}%</span>
            </div>
            <span className="text-[9px] text-slate-400 uppercase tracking-wider font-semibold">so với 1h trước</span>
          </>
        ) : (
          <span className="text-[9px] text-slate-400 uppercase tracking-wider font-semibold">Độ mở van điều áp</span>
        )}
      </div>
    </motion.div>
  );
};


import React from 'react';
import { 
  ResponsiveContainer, 
  AreaChart, 
  Area, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip,
  Legend
} from 'recharts';
import { ChartDataPoint } from '../types';

interface RealTimeChartProps {
  data: ChartDataPoint[];
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="glass-panel border-slate-800/80 p-3 rounded-xl shadow-2xl outline-none">
        <p className="text-[10px] text-slate-400 mb-2 font-mono font-bold tracking-wider">{label}</p>
        <div className="space-y-1.5">
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center justify-between gap-8">
              <span className="text-[10px] font-bold text-slate-300 uppercase tracking-wider">
                {entry.name}
              </span>
              <span className="text-xs font-mono font-bold" style={{ color: entry.color }}>
                {typeof entry.value === 'number' ? `${entry.value.toFixed(4)} kWh` : '--'}
              </span>
            </div>
          ))}
        </div>
      </div>
    );
  }
  return null;
};

export const RealTimeChart: React.FC<RealTimeChartProps> = ({ data }) => {
  return (
    <div className="w-full h-full min-h-[300px] glass-panel rounded-2xl p-5 border shadow-xl">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">SO SÁNH ĐIỆN NĂNG TIÊU THỤ TÍCH LŨY</h3>
          <p className="text-[10px] text-slate-500 font-semibold tracking-wide mt-1">Đối chiếu năng lượng tiêu hao: Hệ thống AI vs Baseline truyền thống (kWh)</p>
        </div>
      </div>

      <div className="h-[250px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -15, bottom: 0 }}>
            <defs>
              <linearGradient id="colorEnergy" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#10b981" stopOpacity={0.25}/>
                <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorEnergyBase" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#ef4444" stopOpacity={0.15}/>
                <stop offset="95%" stopColor="#ef4444" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#1e293b" opacity={0.6} />
            <XAxis 
              dataKey="time" 
              hide 
            />
            <YAxis 
              stroke="#64748b" 
              fontSize={10} 
              tickLine={false} 
              axisLine={false} 
              tickFormatter={(val) => `${val.toFixed(3)} kWh`}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend 
              verticalAlign="bottom" 
              height={36} 
              iconType="circle" 
              wrapperStyle={{ fontSize: '9px', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 700, color: '#94a3b8', paddingTop: '20px' }}
            />
            <Area
              type="monotone"
              dataKey="energy"
              name="Điện năng AI tối ưu"
              stroke="#10b981"
              strokeWidth={2.5}
              fillOpacity={1}
              fill="url(#colorEnergy)"
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="energy_base"
              name="Điện năng Baseline"
              stroke="#ef4444"
              strokeWidth={2}
              fillOpacity={1}
              fill="url(#colorEnergyBase)"
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};


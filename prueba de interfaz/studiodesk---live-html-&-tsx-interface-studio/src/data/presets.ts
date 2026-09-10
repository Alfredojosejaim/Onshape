import { ProjectFile } from '../types';

export const SAMPLE_PROJECTS: { id: string; name: string; description: string; files: ProjectFile[] }[] = [
  {
    id: 'tsx-saas-dashboard',
    name: 'Dashboard SaaS (TSX React)',
    description: 'Componente React TSX con estado en vivo, KPI métricas y filtros dinámicos',
    files: [
      {
        id: 'f-app-tsx',
        name: 'App.tsx',
        type: 'tsx',
        isEntry: true,
        content: `import React, { useState, useEffect } from 'react';

export default function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [revenue, setRevenue] = useState(48250);
  const [visitors, setVisitors] = useState(1420);
  const [isLive, setIsLive] = useState(true);
  const [recentTransactions, setRecentTransactions] = useState([
    { id: 'tx-1', client: 'Acme Corp', amount: '+$1,420.00', status: 'Completado', time: 'Hace 2m' },
    { id: 'tx-2', client: 'Studio Design SL', amount: '+$850.50', status: 'Completado', time: 'Hace 14m' },
    { id: 'tx-3', client: 'Nova Labs', amount: '+$3,200.00', status: 'Pendiente', time: 'Hace 1h' },
  ]);

  // Simulación de actividad en vivo
  useEffect(() => {
    if (!isLive) return;
    const interval = setInterval(() => {
      setVisitors(prev => prev + Math.floor(Math.random() * 5) - 2);
    }, 3000);
    return () => clearInterval(interval);
  }, [isLive]);

  const addSimulatedSale = () => {
    const amount = Math.floor(Math.random() * 900) + 100;
    setRevenue(prev => prev + amount);
    setRecentTransactions(prev => [
      {
        id: 'tx-' + Date.now(),
        client: 'Nuevo Cliente Web',
        amount: \`+$\${amount.toFixed(2)}\`,
        status: 'Completado',
        time: 'Justo ahora'
      },
      ...prev.slice(0, 4)
    ]);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 font-sans p-6 sm:p-8">
      {/* Top Header */}
      <header className="max-w-6xl mx-auto flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-6 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center font-bold text-white shadow-lg shadow-cyan-500/20">
              SD
            </div>
            <div>
              <h1 className="text-xl font-bold text-white tracking-tight">StudioDesk Cloud OS</h1>
              <p className="text-xs text-slate-400">Entorno montado en tiempo de ejecución TSX</p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsLive(!isLive)}
            className={\`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors \${
              isLive
                ? 'bg-emerald-950/60 border-emerald-500/30 text-emerald-400'
                : 'bg-slate-900 border-slate-700 text-slate-400'
            }\`}
          >
            <span className={\`w-2 h-2 rounded-full \${isLive ? 'bg-emerald-400 animate-pulse' : 'bg-slate-500'}\`} />
            {isLive ? 'En Directo' : 'Pausado'}
          </button>

          <button
            onClick={addSimulatedSale}
            className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 active:scale-95 transition-all text-xs font-semibold text-white rounded-lg shadow-md shadow-blue-600/30"
          >
            + Simular Venta
          </button>
        </div>
      </header>

      {/* Main Grid */}
      <main className="max-w-6xl mx-auto mt-6 space-y-6">
        {/* Navigation Tabs */}
        <div className="flex gap-2 border-b border-slate-800 pb-1">
          {['overview', 'analytics', 'reports'].map(tab => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={\`px-4 py-2 text-xs font-medium capitalize rounded-t-lg transition-all \${
                activeTab === tab
                  ? 'bg-slate-800/80 text-cyan-400 border-b-2 border-cyan-400'
                  : 'text-slate-400 hover:text-slate-200'
              }\`}
            >
              {tab === 'overview' ? 'Vista General' : tab === 'analytics' ? 'Analíticas' : 'Informes'}
            </button>
          ))}
        </div>

        {/* Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-sm">
            <span className="text-xs font-medium text-slate-400">Ingresos Totales</span>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-3xl font-bold tracking-tight text-white">
                \${revenue.toLocaleString()}
              </span>
              <span className="text-xs font-medium text-emerald-400">+14.2%</span>
            </div>
            <p className="mt-2 text-xs text-slate-500">Actualizado dinámicamente con React hooks</p>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-sm">
            <span className="text-xs font-medium text-slate-400">Usuarios Activos</span>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-3xl font-bold tracking-tight text-cyan-400">
                {visitors}
              </span>
              <span className="text-xs font-medium text-cyan-500">Live stream</span>
            </div>
            <p className="mt-2 text-xs text-slate-500">Tasa de retención 88.4%</p>
          </div>

          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 backdrop-blur-sm">
            <span className="text-xs font-medium text-slate-400">Rendimiento UI</span>
            <div className="mt-2 flex items-baseline gap-2">
              <span className="text-3xl font-bold tracking-tight text-emerald-400">
                60 FPS
              </span>
              <span className="text-xs font-medium text-emerald-500">Cero lags</span>
            </div>
            <p className="mt-2 text-xs text-slate-500">Montaje en memoria autocontenido</p>
          </div>
        </div>

        {/* Transactions Table */}
        <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-sm font-semibold text-white">Últimas Transacciones</h2>
            <span className="text-xs text-slate-400">{recentTransactions.length} registros</span>
          </div>

          <div className="divide-y divide-slate-800/80">
            {recentTransactions.map(tx => (
              <div key={tx.id} className="py-3 flex items-center justify-between text-xs">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-slate-800 flex items-center justify-center font-bold text-slate-300">
                    {tx.client.charAt(0)}
                  </div>
                  <div>
                    <p className="font-medium text-slate-200">{tx.client}</p>
                    <p className="text-[11px] text-slate-500">{tx.time}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-semibold text-emerald-400">{tx.amount}</p>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800/40">
                    {tx.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
}
`,
      },
    ],
  },
  {
    id: 'html-payment-card',
    name: 'Checkout & Pasarela (HTML + Tailwind)',
    description: 'Página HTML interactiva con formulario de tarjeta y validación en vivo',
    files: [
      {
        id: 'f-index-html',
        name: 'index.html',
        type: 'html',
        isEntry: true,
        content: `<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Checkout Seguro</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex items-center justify-center p-4">
  <div class="w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl p-6 sm:p-8 shadow-2xl">
    <!-- Header -->
    <div class="flex justify-between items-center pb-6 border-b border-slate-800">
      <div>
        <h1 class="text-lg font-bold text-white tracking-tight">Pasarela de Pago</h1>
        <p class="text-xs text-slate-400">Suscripción StudioDesk Pro</p>
      </div>
      <div class="text-right">
        <span class="text-xl font-extrabold text-cyan-400">$29.00</span>
        <span class="text-xs text-slate-500">/mes</span>
      </div>
    </div>

    <!-- Virtual Credit Card Preview -->
    <div class="my-6 relative overflow-hidden h-48 rounded-2xl bg-gradient-to-tr from-indigo-900 via-blue-900 to-slate-900 border border-blue-500/30 p-5 flex flex-col justify-between shadow-xl">
      <div class="flex justify-between items-center">
        <div class="w-10 h-7 bg-amber-400/90 rounded-md shadow-inner flex items-center justify-center">
          <div class="w-6 h-4 border border-amber-600/40 rounded-sm"></div>
        </div>
        <span class="text-xs font-semibold tracking-widest text-slate-300">VISA PRO</span>
      </div>

      <div class="text-center font-mono text-lg tracking-widest text-white drop-shadow" id="card-display-number">
        •••• •••• •••• 4242
      </div>

      <div class="flex justify-between items-end text-xs">
        <div>
          <span class="text-[10px] text-slate-400 block uppercase">Titular</span>
          <span class="font-medium text-slate-200 tracking-wide" id="card-display-name">ALEJANDRO PÉREZ</span>
        </div>
        <div>
          <span class="text-[10px] text-slate-400 block uppercase">Expira</span>
          <span class="font-medium text-slate-200" id="card-display-exp">12/28</span>
        </div>
      </div>
    </div>

    <!-- Payment Form -->
    <form id="payment-form" class="space-y-4" onsubmit="event.preventDefault(); submitPayment();">
      <div>
        <label class="block text-xs font-medium text-slate-300 mb-1">Nombre en la Tarjeta</label>
        <input
          type="text"
          id="card-name-input"
          value="Alejandro Pérez"
          placeholder="Juan García"
          class="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-cyan-500 transition"
          oninput="document.getElementById('card-display-name').innerText = this.value.toUpperCase() || 'TITULAR'"
        />
      </div>

      <div>
        <label class="block text-xs font-medium text-slate-300 mb-1">Número de Tarjeta</label>
        <input
          type="text"
          id="card-num-input"
          value="4242 •••• •••• 4242"
          placeholder="4000 1234 5678 9010"
          class="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs font-mono text-white focus:outline-none focus:border-cyan-500 transition"
          oninput="document.getElementById('card-display-number').innerText = this.value || '•••• •••• •••• ••••'"
        />
      </div>

      <div class="grid grid-cols-2 gap-3">
        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1">Fecha Exp.</label>
          <input
            type="text"
            value="12/28"
            placeholder="MM/AA"
            class="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs text-white focus:outline-none focus:border-cyan-500 transition"
            oninput="document.getElementById('card-display-exp').innerText = this.value || 'MM/AA'"
          />
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1">CVC / CVV</label>
          <input
            type="password"
            maxlength="4"
            value="888"
            placeholder="•••"
            class="w-full px-3.5 py-2.5 bg-slate-950 border border-slate-800 rounded-xl text-xs font-mono text-white focus:outline-none focus:border-cyan-500 transition"
          />
        </div>
      </div>

      <button
        type="submit"
        id="pay-button"
        class="w-full mt-2 py-3 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 active:scale-[0.99] transition-all font-semibold text-xs text-white rounded-xl shadow-lg shadow-cyan-500/25 flex items-center justify-center gap-2 cursor-pointer"
      >
        <span>Confirmar y Pagar $29.00</span>
      </button>

      <div id="success-message" class="hidden p-3 rounded-xl bg-emerald-950/80 border border-emerald-500/40 text-emerald-300 text-xs text-center font-medium animate-fade-in">
        Pago autorizado exitosamente en ejecución en vivo.
      </div>
    </form>
  </div>

  <script>
    function submitPayment() {
      const btn = document.getElementById('pay-button');
      const msg = document.getElementById('success-message');
      btn.disabled = true;
      btn.innerHTML = '<span>Procesando pago seguro...</span>';
      setTimeout(() => {
        btn.innerHTML = '<span>Pago Realizado</span>';
        btn.className = 'w-full mt-2 py-3 bg-emerald-600 text-white font-semibold text-xs rounded-xl';
        msg.classList.remove('hidden');
        console.log('[StudioDesk Runtime] Transacción procesada por valor de $29.00');
      }, 900);
    }
  </script>
</body>
</html>
`,
      },
    ],
  },
  {
    id: 'tsx-kanban-flow',
    name: 'Kanban Task Board (TSX React)',
    description: 'Gestor interactivo de tareas con filtros, drag & drop de estado y contador de métricas',
    files: [
      {
        id: 'f-kanban-tsx',
        name: 'App.tsx',
        type: 'tsx',
        isEntry: true,
        content: `import React, { useState } from 'react';

interface Task {
  id: string;
  title: string;
  tag: string;
  column: 'todo' | 'doing' | 'done';
}

export default function KanbanBoard() {
  const [tasks, setTasks] = useState<Task[]>([
    { id: '1', title: 'Importar módulo HTML a StudioDesk', tag: 'UI Core', column: 'done' },
    { id: '2', title: 'Montar compilador TSX en vivo', tag: 'Runtime', column: 'done' },
    { id: '3', title: 'Añadir soporte PWA autocontenido', tag: 'Desktop', column: 'doing' },
    { id: '4', title: 'Inspector visual bidireccional', tag: 'Feature', column: 'todo' },
  ]);
  const [newTitle, setNewTitle] = useState('');

  const addTask = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newTitle.trim()) return;
    setTasks(prev => [
      ...prev,
      {
        id: Date.now().toString(),
        title: newTitle.trim(),
        tag: 'User Task',
        column: 'todo'
      }
    ]);
    setNewTitle('');
  };

  const moveTask = (id: string, nextCol: 'todo' | 'doing' | 'done') => {
    setTasks(prev => prev.map(t => t.id === id ? { ...t, column: nextCol } : t));
  };

  const columns = [
    { id: 'todo', label: 'Por Hacer', color: 'border-amber-500/40 text-amber-400' },
    { id: 'doing', label: 'En Progreso', color: 'border-cyan-500/40 text-cyan-400' },
    { id: 'done', label: 'Completado', color: 'border-emerald-500/40 text-emerald-400' },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-6 font-sans">
      <div className="max-w-5xl mx-auto space-y-6">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">Tablero de Tareas Sprint</h1>
            <p className="text-xs text-slate-400">Montaje interactivo React TSX</p>
          </div>

          <form onSubmit={addTask} className="flex gap-2 w-full sm:w-auto">
            <input
              type="text"
              placeholder="Nueva tarea..."
              value={newTitle}
              onChange={e => setNewTitle(e.target.value)}
              className="px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white focus:outline-none focus:border-cyan-500"
            />
            <button
              type="submit"
              className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-xs font-semibold text-white rounded-lg transition"
            >
              + Añadir
            </button>
          </form>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {columns.map(col => {
            const colTasks = tasks.filter(t => t.column === col.id);
            return (
              <div key={col.id} className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-4 flex flex-col min-h-[360px]">
                <div className="flex justify-between items-center pb-3 border-b border-slate-800">
                  <span className={\`text-xs font-bold uppercase tracking-wider \${col.color}\`}>
                    {col.label}
                  </span>
                  <span className="text-[11px] px-2 py-0.5 bg-slate-800 rounded-full text-slate-400 font-semibold">
                    {colTasks.length}
                  </span>
                </div>

                <div className="mt-3 space-y-3 flex-1">
                  {colTasks.map(task => (
                    <div
                      key={task.id}
                      className="p-3 bg-slate-800/80 hover:bg-slate-800 border border-slate-700/60 rounded-xl transition shadow-sm space-y-2"
                    >
                      <span className="text-[10px] px-2 py-0.5 rounded bg-slate-900 text-cyan-300 font-medium">
                        {task.tag}
                      </span>
                      <p className="text-xs font-medium text-slate-100">{task.title}</p>

                      <div className="pt-2 flex justify-end gap-1.5 text-[10px]">
                        {task.column !== 'todo' && (
                          <button
                            onClick={() => moveTask(task.id, task.column === 'done' ? 'doing' : 'todo')}
                            className="px-2 py-0.5 bg-slate-700/80 hover:bg-slate-600 rounded text-slate-300"
                          >
                            ←
                          </button>
                        )}
                        {task.column !== 'done' && (
                          <button
                            onClick={() => moveTask(task.id, task.column === 'todo' ? 'doing' : 'done')}
                            className="px-2 py-0.5 bg-cyan-900/80 hover:bg-cyan-800 text-cyan-200 rounded"
                          >
                            →
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
`,
      },
    ],
  },
];

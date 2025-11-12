document.addEventListener('DOMContentLoaded', () => {
  const socket = io();
  let processCounter = 1;
  let cpuHistory = [];
  let processMeta = new Map();

  // --- Seletores de Elementos
  const addProcessBtn = document.getElementById('add-process');
  const addRandomBtn = document.getElementById('add-random-process');
  const clearBtn = document.getElementById('clear-simulation');
  const processList = document.getElementById('process-list');
  const startBtn = document.getElementById('start-simulation');
  const algorithmSelect = document.getElementById('algorithm-select');
  const quantumConfig = document.getElementById('quantum-config');
  const timeline = document.getElementById('timeline');
  const cpuBox = document.getElementById('cpu-box');
  const queuesArea = document.getElementById('queues-area');
  const completedProcesses = document.getElementById('completed-processes');
  const statsArea = document.getElementById('stats-area');
  const statsTable = document.getElementById('stats-table');
  const avgWaitSpan = document.getElementById('avg-wait');
  const avgTurnaroundSpan = document.getElementById('avg-turnaround');


  function toggleAlgorithmFields() {
    const selectedAlgo = algorithmSelect.value;
    const priorityCols = document.querySelectorAll('.priority-col');
    quantumConfig.style.display = 'none';
    priorityCols.forEach(col => col.style.display = 'none');
    if (selectedAlgo === 'round_robin') {
      quantumConfig.style.display = 'block';
    } else if (selectedAlgo === 'multi_level') {
      priorityCols.forEach(col => col.style.display = 'table-cell');
    }
  }


  function createProcessPill(p, context = 'queue') {
    const pill = document.createElement('div');
    pill.className = 'process-pill';
    const pillText = document.createElement('span');
    pillText.className = 'process-pill-text';
    pillText.textContent = p.pid;

    if (context === 'cpu') {
      pill.classList.add('cpu-color');
      const progressBar = document.createElement('div');
      progressBar.className = 'process-progress';
      let progress = 0;
      if (p.burst_time > 0) {
        progress = ((p.burst_time - p.remaining_time) / p.burst_time) * 100;
      }
      progressBar.style.width = `${progress}%`;
      pill.appendChild(progressBar);
      pill.appendChild(pillText);
    } else if (context === 'queue') {
      pill.classList.add('queue-color');
      pill.appendChild(pillText);
    } else if (context === 'completed') {
      pill.classList.add('completed-color');
      pill.appendChild(pillText);
    }
    return pill;
  }

  function addProcessRow() {
    const currentProcessCount = processList.children.length;
    if (currentProcessCount >= 5) {
      alert("Você pode adicionar no máximo 5 processos.");
      return;
    }
    const pid = `P${processCounter++}`;
    const row = document.createElement('tr');
    row.innerHTML = `
      <td><input type="text" class="form-control form-control-sm pid" value="${pid}" readonly></td>
      <td><input type="number" class="form-control form-control-sm arrival" value="0" min="0"></td>
      <td><input type="number" class="form-control form-control-sm burst" value="1" min="1"></td>
      <td class="priority-col" style="display: none;">
        <input type="number" class="form-control form-control-sm priority" value="0" min="1" max="2">
      </td>
      <td><button class="btn btn-sm btn-danger remove-process">Remover</button></td>
    `;
    processList.appendChild(row);
    row.querySelector('.remove-process').addEventListener('click', () => row.remove());
    toggleAlgorithmFields();
  }


  function resetSimulationOutput() {
    cpuBox.textContent = 'Idle';
    cpuBox.classList.remove('cpu');
    queuesArea.innerHTML = '';
    completedProcesses.innerHTML = '';
    statsArea.style.display = 'none';
    statsTable.innerHTML = '';
    avgWaitSpan.textContent = '';
    avgTurnaroundSpan.textContent = '';
    startBtn.disabled = false;

    const timelineContainer = document.getElementById('gantt-timeline');
    const chartContainer = document.getElementById('gantt-chart');
    if (timelineContainer) timelineContainer.innerHTML = '';
    if (chartContainer) chartContainer.innerHTML = '';
  }

  function clearAllData() {
    resetSimulationOutput();
    processCounter = 1;
    processList.innerHTML = '';
  }

  // Função do Diagrama de Gantt
  function renderGanttChart(history, mode = 'single') {
    const timelineEl = document.getElementById('gantt-timeline');
    const chartEl = document.getElementById('gantt-chart');
    if (!timelineEl || !chartEl || !history || history.length === 0) return;

    const N = history.length;
    const colWidth = 32;
    const labelColPx = 110;

    const PID_PALETTE = {
    P1: { bg: '#1f77b4', border: '#165a88', fg: '#ffffff' }, 
    P2: { bg: '#ff7f0e', border: '#cc650b', fg: '#000000' }, 
    P3: { bg: '#2ca02c', border: '#1f7a1f', fg: '#ffffff' }, 
    P4: { bg: '#d62728', border: '#a51f20', fg: '#ffffff' }, 
    P5: { bg: '#9467bd', border: '#6f4e8f', fg: '#ffffff' }, 
    };

    // --- Helpers ---
    const mk = (cls, text = '') => {
      const d = document.createElement('div');
      d.className = cls;
      if (text !== null) d.textContent = text;
      return d;
    };
    const colorForPid = (pid) => {
    if (pid === 'Idle') return { bg: '#f8f9fa', border: '#ced4da', fg: '#777d6cff', dashed: true };

     const fixed = PID_PALETTE[pid];
     if (fixed) return { ...fixed, dashed: false };
    let h = 0;
    const s = String(pid);
    for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 360;
    return { bg: `hsl(${h} 65% 40%)`, border: `hsl(${h} 65% 32%)`, fg: '#fff', dashed: false };
    };

    const segments = [];
    let start = 0;
    for (let i = 1; i <= N; i++) {
      if (i === N || history[i] !== history[i - 1]) {
        segments.push({ pid: history[i - 1], start, end: i }); 
        start = i;
      }
    }

    // Limpa containers
    timelineEl.innerHTML = '';
    chartEl.innerHTML = '';

    // Cabeçalho do tempo (grade)
    timelineEl.style.display = 'grid';
    timelineEl.style.gridTemplateColumns = `${labelColPx}px repeat(${N}, ${colWidth}px)`;
    timelineEl.style.alignItems = 'center';
    timelineEl.style.gap = '2px';

    timelineEl.appendChild(mk('gantt-head', 'Tempo'));
    for (let t = 0; t < N; t++) timelineEl.appendChild(mk('gantt-time', String(t)));

    
    if (mode === 'single') {
      chartEl.style.display = 'grid';
      chartEl.style.gridTemplateColumns = `${labelColPx}px repeat(${N}, ${colWidth}px)`;
      chartEl.style.alignItems = 'center';
      chartEl.style.gap = '2px';

      // rótulo da linha
      chartEl.appendChild(mk('gantt-head', 'Processo'));

      // preenche célula por tick, com PID completo e tooltip
      for (let i = 0; i < N; i++) {
        const pid = history[i];
        const cell = mk('gantt-cell', pid === 'Idle' ? '' : String(pid));
        const c = colorForPid(pid);
        cell.style.background = c.bg;
        cell.style.border = `1px ${c.dashed ? 'dashed' : 'solid'} ${c.border}`;
        cell.style.color = c.fg;

        
        const meta = processMeta.get(pid);
        cell.title = (pid === 'Idle') ?
          `Idle (t=${i})` :
          `${pid}\nTick: ${i}\n` +
          (meta ? `Chegada: ${meta.arrival} | Burst: ${meta.burst}` : '');

        chartEl.appendChild(cell);
      }
      return;
    }

    chartEl.style.display = 'flex';
    chartEl.style.flexDirection = 'column';
    chartEl.style.gap = '8px';

   
    const pids = [...new Set(segments.map(s => s.pid))];
    const idleIdx = pids.indexOf('Idle');
    if (idleIdx !== -1) { pids.splice(idleIdx, 1); pids.push('Idle'); }

    pids.forEach(pid => {
      
      const row = document.createElement('div');
      row.className = 'gantt-row';
      row.style.display = 'grid';
      row.style.gridTemplateColumns = `${labelColPx}px ${N * colWidth + (N - 1) * 2}px`;
      row.style.alignItems = 'center';
      row.style.columnGap = '8px';

      const label = mk('gantt-row-label', pid === 'Idle' ? 'Idle' : String(pid));
      row.appendChild(label);

      const track = mk('gantt-row-track', null);
      track.style.position = 'relative';
      track.style.height = '28px';
      row.appendChild(track);

     
      segments.filter(s => s.pid === pid).forEach(s => {
        const bar = mk('gantt-bar', pid === 'Idle' ? '' : String(pid));
        const c = colorForPid(pid);
        bar.style.background = c.bg;
        bar.style.border = `1px ${c.dashed ? 'dashed' : 'solid'} ${c.border}`;
        bar.style.color = c.fg;

        const widthPx = (s.end - s.start) * (colWidth + 2) - 2;
        const leftPx = s.start * (colWidth + 2);

        bar.style.position = 'absolute';
        bar.style.left = `${leftPx}px`;
        bar.style.width = `${widthPx}px`;
        bar.style.top = 0;
        bar.style.bottom = 0;

        const meta = processMeta.get(pid);
        bar.title = (pid === 'Idle') ?
          `Idle: ${s.start}–${s.end} (dur. ${s.end - s.start})` :
          `${pid}: ${s.start}–${s.end} (dur. ${s.end - s.start})\n` +
          (meta ? `Chegada: ${meta.arrival} | Burst: ${meta.burst}` : '');

        track.appendChild(bar);
      });

      chartEl.appendChild(row);
    });
  }
  
  addProcessBtn.addEventListener('click', addProcessRow);


  addRandomBtn.addEventListener('click', () => {
    addProcessRow();
    const newRow = processList.lastElementChild;
    if (!newRow) return;
    const randomArrival = Math.floor(Math.random() * 21);
    const randomBurst = Math.floor(Math.random() * 10) + 1;
    const randomPriority = Math.floor(Math.random() * 2);
    newRow.querySelector('.arrival').value = randomArrival;
    newRow.querySelector('.burst').value = randomBurst;
    newRow.querySelector('.priority').value = randomPriority;
  });

  clearBtn.addEventListener('click', clearAllData);

  algorithmSelect.addEventListener('change', toggleAlgorithmFields);

  startBtn.addEventListener('click', () => {
    cpuHistory = [];
    const processes = [];
    processMeta.clear();
    
    
    processList.querySelectorAll('tr').forEach(row => {
      const processData = {
        pid: row.querySelector('.pid').value,
        arrival: parseInt(row.querySelector('.arrival').value, 10) || 0,
        burst: parseInt(row.querySelector('.burst').value, 10) || 1
      };
      const priorityInput = row.querySelector('.priority');
      if (priorityInput && window.getComputedStyle(priorityInput.parentElement).display !== 'none') {
        const userPriority = parseInt(priorityInput.value, 10) || 1;
        processData.priority = userPriority - 1
      }
      processes.push(processData);
    });

    // Populando o processMeta com os dados lidos da tabela
    processes.forEach(p => {
      processMeta.set(p.pid, { arrival: p.arrival, burst: p.burst });
    });

    const algorithm = algorithmSelect.value;
    const quantum = document.getElementById('quantum').value;
    resetSimulationOutput();
    startBtn.disabled = true;
    socket.emit('start_simulation', { processes, algorithm, quantum });
  });

  // --- Socket Listeners (sem alteração) ---
  socket.on('simulation_update', (data) => {
    const currentCpuPid = (data.cpu && data.cpu.pid) ? data.cpu.pid : 'Idle';
    cpuHistory.push(currentCpuPid);

    //timeline.textContent = data.time;
    cpuBox.innerHTML = '';
    if (data.cpu && data.cpu !== 'Idle') {
      const pill = createProcessPill(data.cpu, 'cpu');
      cpuBox.appendChild(pill);
    } else {
      cpuBox.textContent = 'Idle';
    }
    queuesArea.innerHTML = '';
    if (data.ready_queues) {
      data.ready_queues.forEach((queue, index) => {
        const col = document.createElement('div');
        col.className = 'col';
        col.innerHTML = `<h6>Fila Prioridade ${index + 1}</h6>`;
        const queueBox = document.createElement('div');
        queueBox.className = 'process-box queue';
        queue.forEach(p => queueBox.appendChild(createProcessPill(p, 'queue')));
        col.appendChild(queueBox);
        queuesArea.appendChild(col);
      });
    } else if (data.ready_queue) {
      const col = document.createElement('div');
      col.className = 'col-12';
      const queueBox = document.createElement('div');
      queueBox.className = 'process-box queue';
      data.ready_queue.forEach(p => queueBox.appendChild(createProcessPill(p, 'queue')));
      col.appendChild(queueBox);
      queuesArea.appendChild(col);
    }
    completedProcesses.innerHTML = '';
    if (data.completed && data.completed.length > 0) {
      completedProcesses.classList.add('completed');
      data.completed.forEach(p => {
        completedProcesses.appendChild(createProcessPill(p, 'completed'));
      });
    }
  });

  socket.on('simulation_end', (data) => {
    renderGanttChart(cpuHistory);
    avgWaitSpan.textContent = data.avg_wait.toFixed(2);
    avgTurnaroundSpan.textContent = data.avg_turnaround.toFixed(2);
    statsTable.innerHTML = '';
    data.stats.forEach(p => {
      const row = document.createElement('tr');
      row.innerHTML = `
        <td>${p.pid}</td>
        <td>${p.waiting_time}</td>
        <td>${p.turnaround_time}</td>
      `;
      statsTable.appendChild(row);
    });
    statsArea.style.display = 'block';
    startBtn.disabled = false;
  });

  // --- Inicialização da Página ---
  addProcessRow();
  toggleAlgorithmFields();
});
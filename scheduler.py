import collections
import heapq
from typing import Any, Generator, Deque, List, Optional, Tuple

# =====================================================================
# CLASSE DE PROCESSO (Inalterada)
# =====================================================================
class Process:
    def __init__(self, pid: str, arrival_time: int, burst_time: int, priority: int = 0):
        self.pid = pid
        self.arrival_time = int(arrival_time)
        self.burst_time = int(burst_time)
        self.priority = int(priority)
        self.remaining_time = int(burst_time)
        self.start_time = -1
        self.completion_time = -1
        self.waiting_time = 0
        self.turnaround_time = 0

    def __lt__(self, other: 'Process') -> bool:
        return self.remaining_time < other.remaining_time

# =====================================================================
# FUNÇÕES AUXILIARES (HELPERS - Inalteradas)
# =====================================================================

def _add_arriving_processes(processes: list[Process], p_idx: int, time: int, queue: collections.deque) -> int:
    while p_idx < len(processes) and processes[p_idx].arrival_time <= time:
        queue.append(processes[p_idx])
        p_idx += 1
    return p_idx

def _add_arriving_processes_heap(processes: list[Process], p_idx: int, time: int, heap: list[Process]) -> int:
    while p_idx < len(processes) and processes[p_idx].arrival_time <= time:
        heapq.heappush(heap, processes[p_idx])
        p_idx += 1
    return p_idx

def _add_arriving_processes_multi_queue(processes: list[Process], p_idx: int, time: int, queues: list[collections.deque]) -> int:
    while p_idx < len(processes) and processes[p_idx].arrival_time <= time:
        p = processes[p_idx]
        if 0 <= p.priority < len(queues):
            queues[p.priority].append(p)
        p_idx += 1
    return p_idx

def _finalize_process(process: Process, time: int, completed: list[Process]):
    process.completion_time = time
    process.turnaround_time = process.completion_time - process.arrival_time
    process.waiting_time = process.turnaround_time - process.burst_time
    completed.append(process)

def _update_running_process(process: Process | None, time: int, completed: list[Process]) -> Process | None:
    if not process:
        return None
    
    process.remaining_time -= 1
    if process.remaining_time == 0:
        _finalize_process(process, time, completed)
        return None
    return process

def _handle_rr_tick(
    current_p: Optional[Process], 
    time_slice: int, 
    quantum: int, 
    time: int, 
    ready_queue: Deque[Process], 
    completed: List[Process]
) -> Tuple[Optional[Process], int]:
    if not current_p:
        return None, time_slice

    current_p.remaining_time -= 1
    time_slice += 1

    if current_p.remaining_time == 0:
        _finalize_process(current_p, time, completed)
        return None, 0

    if time_slice == quantum:
        ready_queue.append(current_p)
        return None, 0

    return current_p, time_slice

def _select_new_process_from_heap(p: Process | None, heap: list[Process], time: int) -> Process | None:
    if not p and heap:
        new_p = heapq.heappop(heap)
        if new_p.start_time == -1:
            new_p.start_time = time
        return new_p
    
    if p and heap and heap[0].remaining_time < p.remaining_time:
        heapq.heappush(heap, p)
        new_p = heapq.heappop(heap)
        if new_p.start_time == -1:
            new_p.start_time = time
        return new_p
        
    return p

def _select_new_process_from_multi_queue(p: Process | None, queues: list[collections.deque], time: int) -> Process | None:
    highest_prio_idx = -1
    for i, q in enumerate(queues):
        if q:
            highest_prio_idx = i
            break
    
    if p and highest_prio_idx != -1 and p.priority > highest_prio_idx:
        queues[p.priority].appendleft(p)
        p = None

    if not p:
        for q in queues:
            if q:
                p = q.popleft()
                if p.start_time == -1:
                    p.start_time = time
                break
    return p

# =====================================================================
# FUNÇÕES PRINCIPAIS DO SCHEDULER (COM ALTERAÇÕES)
# =====================================================================

# scheduler.py (OTIMIZADO - EVENT-DRIVEN)
def fcfs_scheduler_optimized(processes: list["Process"]) -> Generator[dict[str, Any], Any, None]:
   
    processes.sort(key=lambda p: p.arrival_time)

    ready_queue = collections.deque()
    completed = []
    n = len(processes)

    time = 0
    p_idx = 0        # índice do próximo processo a chegar (na lista ordenada)
    current_p = None

    while len(completed) < n:
        # 1) Adiciona todos que já chegaram até 'time'
        p_idx = _add_arriving_processes(processes, p_idx, time, ready_queue)

        # 2) Se não há processo rodando, tenta pegar da fila
        if current_p is None:
            if ready_queue:
                current_p = ready_queue.popleft()
                if current_p.start_time == -1:
                    current_p.start_time = time

                # Evento de INÍCIO
                yield {
                    'time': time,
                    'cpu': vars(current_p),
                    'ready_queue': [vars(p) for p in ready_queue],
                    'event': 'START'
                }

            else:
                # Fila vazia. Se ainda há processos que chegarão no futuro, pula para a próxima chegada
                if p_idx < n:
                    next_arrival = processes[p_idx].arrival_time
                    # Evento de OCIOSIDADE
                    yield {
                        'time': time,
                        'cpu': 'Idle',
                        'ready_queue': [],
                        'event': f'IDLE_UNTIL_{next_arrival}'
                    }
                    time = next_arrival
                    continue
                else:
                    # Nada a executar e ninguém mais chegará
                    break

        # 3) Se há processo rodando (FCFS = não-preemptivo), roda até terminar
        finish_time = time + current_p.remaining_time

        # Durante a execução, outros processos podem chegar; apenas entram na fila
        while p_idx < n and processes[p_idx].arrival_time <= finish_time:
            # Empilha todas as chegadas até o término do atual
            ready_queue.append(processes[p_idx])
            p_idx += 1

        # Avança o relógio até o término do processo atual
        time = finish_time
        current_p.remaining_time = 0

        # Finaliza o processo atual
        _finalize_process(current_p, time, completed)
        current_p = None

        # Evento de TÉRMINO
        yield {
            'time': time,
            'cpu': 'Idle',
            'ready_queue': [vars(p) for p in ready_queue],
            'event': 'FINISH'
        }

    # Estatísticas finais
    yield {'final_stats': [vars(p) for p in completed]}
    yield {'time': time, 'cpu': 'Idle', 'ready_queue': [], 'completed': [vars(p) for p in completed]}
    

def rr_scheduler(processes: list[Process], quantum: int) -> Generator[dict[str, Any], Any, None]:
    processes.sort(key=lambda p: p.arrival_time)
    ready_queue = collections.deque()
    completed = []
    time, p_idx, current_p, time_slice = 0, 0, None, 0

    while p_idx < len(processes) or ready_queue or current_p:
        p_idx = _add_arriving_processes(processes, p_idx, time, ready_queue)
        
        if not current_p and ready_queue:
            current_p = ready_queue.popleft()
            if current_p.start_time == -1:
                current_p.start_time = time
            time_slice = 0

        # ALTERADO: Envia o objeto completo (vars(p)) em vez de apenas p.pid
        yield {
            'time': time, 
            'cpu': vars(current_p) if current_p else 'Idle', 
            'ready_queue': [vars(p) for p in ready_queue], 
            'completed': [vars(p) for p in completed]
        }
        
        time += 1
        current_p, time_slice = _handle_rr_tick(
            current_p, time_slice, quantum, time, ready_queue, completed
        )

    yield {'final_stats': [vars(p) for p in completed]}
    yield {'time': time, 'cpu': 'Idle', 'ready_queue': [], 'completed': [vars(p) for p in completed]}

def sjf_preemptive_scheduler(processes: list[Process]) -> Generator[dict[str, Any], Any, None]:
    processes.sort(key=lambda p: p.arrival_time)
    ready_heap = []
    completed = []
    time, p_idx, current_p = 0, 0, None

    while p_idx < len(processes) or ready_heap or current_p:
        p_idx = _add_arriving_processes_heap(processes, p_idx, time, ready_heap)
        current_p = _select_new_process_from_heap(current_p, ready_heap, time)

        # ALTERADO: Envia o objeto completo (vars(p)) em vez de apenas p.pid
        yield {
            'time': time, 
            'cpu': vars(current_p) if current_p else 'Idle', 
            'ready_queue': [vars(p) for p in sorted(ready_heap)], 
            'completed': [vars(p) for p in completed]
        }
        
        time += 1
        current_p = _update_running_process(current_p, time, completed)

    yield {'final_stats': [vars(p) for p in completed]}
    yield {'time': time, 'cpu': 'Idle', 'ready_queue': [], 'completed': [vars(p) for p in completed]}

def multi_level_queue_scheduler(processes: list[Process]) -> Generator[dict[str, Any], Any, None]:
    processes.sort(key=lambda p: p.arrival_time)
    ready_queues = [collections.deque() for _ in range(3)] 
    completed = []
    time, p_idx, current_p = 0, 0, None

    while p_idx < len(processes) or any(ready_queues) or current_p:
        p_idx = _add_arriving_processes_multi_queue(processes, p_idx, time, ready_queues)
        current_p = _select_new_process_from_multi_queue(current_p, ready_queues, time)

        yield {
            'time': time,
            'cpu': vars(current_p) if current_p else 'Idle',
            'ready_queues': [[vars(p) for p in q] for q in ready_queues],
            'completed': [vars(p) for p in completed]
        }

        time += 1
        current_p = _update_running_process(current_p, time, completed)
    
    yield {'final_stats': [vars(p) for p in completed]}
    yield {'time': time, 'cpu': 'Idle', 'ready_queue': [], 'completed': [vars(p) for p in completed]}
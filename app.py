from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from scheduler import Process, fcfs_scheduler_optimized, multi_level_queue_scheduler, sjf_preemptive_scheduler, rr_scheduler

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('index.html')

SCHEDULER_MAP = {
    'fcfs': fcfs_scheduler_optimized,
    'sjf_preemptive': sjf_preemptive_scheduler,
    'round_robin': rr_scheduler,
    'multi_level': multi_level_queue_scheduler
}


@socketio.on('start_simulation')
def handle_simulation(data):
    processes_data = data['processes']
    algorithm = data['algorithm']
    
   
    quantum = data.get('quantum', 0) 
    
    
    processes = [Process(p['pid'], p['arrival'], p['burst'], p.get('priority', 0)) for p in processes_data]
    
    scheduler_generator = None
    if algorithm == 'fcfs':
        scheduler_generator = fcfs_scheduler_optimized(processes)
    elif algorithm == 'sjf_preemptive':
        scheduler_generator = sjf_preemptive_scheduler(processes)
    elif algorithm == 'round_robin':
        scheduler_generator = rr_scheduler(processes, int(quantum))
    elif algorithm == 'multi_level':
        scheduler_generator = multi_level_queue_scheduler(processes)
    

    if scheduler_generator:
        for state in scheduler_generator:
            if 'final_stats' in state:
                
                stats = state['final_stats']
                if not stats:
                   
                    socketio.emit('simulation_end', {'stats': [], 'avg_wait': 0, 'avg_turnaround': 0})
                    return

                avg_wait = sum(p['waiting_time'] for p in stats) / len(stats)
                avg_turnaround = sum(p['turnaround_time'] for p in stats) / len(stats)
                socketio.emit('simulation_end', {'stats': stats, 'avg_wait': avg_wait, 'avg_turnaround': avg_turnaround})
            else:
                socketio.emit('simulation_update', state)
                socketio.sleep(0.7)

def run_simulation_for_user(sid, algorithm_name, processes_data, quantum_str):
    """
    Esta função é executada em background.
    Ela executa a simulação completa para UM único usuário (identificado pelo 'sid')
    e envia os resultados APENAS para ele.
    """
    try:
        
        processes = [Process(p['pid'], p['arrival'], p['burst'], p.get('priority', 0)) for p in processes_data]
        
        # 2. Encontra a função de escalonamento correta
        scheduler_func = SCHEDULER_MAP.get(algorithm_name)
        if not scheduler_func:
            # Se o algoritmo não for encontrado, avisa o usuário
            emit('simulation_error', {'error': f'Algoritmo desconhecido: {algorithm_name}'}, to=sid)
            return

        # 3. Prepara os argumentos para a função (algumas precisam do quantum)
        args = [processes]
        if algorithm_name == 'round_robin':
            args.append(int(quantum_str))
        
        # 4. Cria o gerador da simulação
        scheduler_generator = scheduler_func(*args)

        # 5. Executa a simulação passo a passo
        if scheduler_generator:
            for state in scheduler_generator:
                if 'final_stats' in state:
                    
                    stats = state['final_stats']
                    if not stats:
                        
                        emit('simulation_end', {'stats': [], 'avg_wait': 0, 'avg_turnaround': 0}, to=sid)
                        return

                    
                    avg_wait = sum(p['waiting_time'] for p in stats) / len(stats)
                    avg_turnaround = sum(p['turnaround_time'] for p in stats) / len(stats)
                    
                    
                    emit('simulation_end', {'stats': stats, 'avg_wait': avg_wait, 'avg_turnaround': avg_turnaround}, to=sid)
                else:
                    
                    emit('simulation_update', state, to=sid)
                    socketio.sleep(0.7)

    except Exception as e:
        
        print(f"Erro na simulação para {sid}: {e}")
        emit('simulation_error', {'error': str(e)}, to=sid)

@socketio.on('start_simulation')
def handle_start_simulation(data):
    """
    Disparado quando QUALQUER usuário clica em 'Iniciar Simulação'.
    """
    
    user_sid = request.sid
    
  
    processes = data.get('processes', [])
    algorithm = data.get('algorithm', 'fcfs')
    quantum = data.get('quantum', '0')
    
    
    socketio.start_background_task(
        target=run_simulation_for_user,
        sid=user_sid,
        algorithm_name=algorithm,
        processes_data=processes,
        quantum_str=quantum
    )

@socketio.on('connect')
def handle_connect():
    """Apenas para debug, para vermos quem está conectando."""
    print(f'Cliente conectado: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    """Apenas para debug."""
    print(f'Cliente desconectado: {request.sid}')


if __name__ == '__main__':
    socketio.run(app, debug=True)